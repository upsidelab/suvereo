from django.contrib.auth.models import Group, Permission
from guardian.shortcuts import assign_perm, get_objects_for_user
from rest_framework import serializers

from account.authorization import (
    ADMIN_GROUP_NAME,
    DATASET_PERMISSION_CODENAMES,
    GLOBAL_PERMISSION_CODENAMES,
    PERM_VIEW_DATASET,
    assert_group_ids_assignable,
    assert_not_self_removing_from_admin,
    assert_service_account_admin_assignable,
    assert_user_deactivatable,
    is_application_admin,
    remove_all_dataset_grants,
    set_application_admin,
)
from account.models import DatasetRole, User
from catalog.models import DataSet

from .services import ServiceAccountNameService

_DATASET_PERMISSION_BARE_CODENAMES = {c.split(".")[-1] for c in DATASET_PERMISSION_CODENAMES}


class AccountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    is_admin = serializers.BooleanField(read_only=True)
    permissions = serializers.SerializerMethodField()

    def get_permissions(self, obj):
        """The subset of GLOBAL_PERMISSION_CODENAMES this user actually holds -- lets the
        frontend show/hide global management nav entries per-permission instead of only
        by is_admin."""
        return [codename for codename in GLOBAL_PERMISSION_CODENAMES if obj.has_perm(codename)]


class UserSerializer(serializers.Serializer):
    """Read-only representation used for GET (list) responses."""

    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField()
    is_active = serializers.BooleanField()
    is_admin = serializers.SerializerMethodField()
    group_ids = serializers.SerializerMethodField()

    def get_is_admin(self, obj):
        return is_application_admin(obj)

    def get_group_ids(self, obj):
        return list(obj.groups.values_list("id", flat=True))


class GroupAssignmentValidationMixin:
    """Shared `validate_group_ids` guarding every write path that assigns `group_ids`.

    Blocks a non-Admin requesting user from assigning a group that grants Admin-equivalent
    power (see `account.authorization.assert_group_ids_assignable`). Requires the request in
    `self.context["request"]` — DRF's generic views supply this automatically via
    `get_serializer()`; call sites that instantiate the serializer directly must pass
    `context={"request": request}` explicitly, or the check is skipped (trusted, requestless
    contexts such as management commands).
    """

    def validate_group_ids(self, value):
        request = self.context.get("request")
        if request is not None:
            assert_group_ids_assignable(request.user, value)
            if self.instance is not None:
                assert_not_self_removing_from_admin(request.user, self.instance, value)
        return value


class UserCreateSerializer(GroupAssignmentValidationMixin, serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    is_active = serializers.BooleanField()
    group_ids = serializers.ListField(child=serializers.IntegerField())


class UserUpdateSerializer(GroupAssignmentValidationMixin, serializers.Serializer):
    email = serializers.EmailField()
    is_active = serializers.BooleanField()
    group_ids = serializers.ListField(child=serializers.IntegerField())

    def validate(self, attrs):
        request = self.context.get("request")
        if request is not None and self.instance is not None and attrs.get("is_active") is False:
            assert_user_deactivatable(request.user, self.instance)
        return attrs


class UserUpdatePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)


class CreateUpdateServiceAccountSerializer(serializers.Serializer):
    """Service accounts don't compose Global Roles at all -- either `is_admin` (the Admin group,
    same as a human user's Admin toggle) or an exact, explicit dataset-scoped permission_ids set
    applied uniformly to every listed data_set_ids. Nothing implicit, nothing inherited: a
    non-admin service account holds precisely what's checked here, on precisely these datasets,
    and nothing anywhere else.
    """

    name = serializers.CharField(write_only=True)
    is_active = serializers.BooleanField(default=True)
    is_admin = serializers.BooleanField(default=False)
    permission_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        required=False,
        queryset=Permission.objects.filter(codename__in=_DATASET_PERMISSION_BARE_CODENAMES),
    )
    data_set_ids = serializers.ListField(child=serializers.IntegerField(), required=False)

    def validate(self, attrs):
        request = self.context.get("request")
        if request is None:
            return attrs
        if attrs.get("is_admin"):
            assert_service_account_admin_assignable(request.user, attrs["is_admin"])
        if self.instance is not None and attrs.get("is_active") is False:
            assert_user_deactivatable(request.user, self.instance)
        return attrs

    def create(self, validated_data):
        email = self._build_service_account_email(validated_data.get("name"))
        service_account = User.objects.create_service_account(
            email=email, is_active=validated_data.get("is_active")
        )
        self._apply_admin_and_access(service_account, validated_data)
        return service_account

    def update(self, instance, validated_data):
        instance.email = self._build_service_account_email(validated_data.get("name"))
        instance.is_active = validated_data.get("is_active")
        instance.save()
        self._apply_admin_and_access(instance, validated_data)
        return instance

    def _build_service_account_email(self, name):
        service = ServiceAccountNameService()
        return service.generate_service_account_email(name)

    def _apply_admin_and_access(self, service_account, validated_data):
        is_admin = validated_data.get("is_admin", False)
        set_application_admin(service_account, is_admin)
        if is_admin:
            self._sync_data_sets(service_account, [], [])
        else:
            self._sync_data_sets(
                service_account, validated_data.get("data_set_ids", []), validated_data.get("permission_ids", [])
            )

    def _sync_data_sets(self, service_account, data_set_ids, permissions):
        """Replace every dataset-access grant this service account holds with exactly
        `permissions` on exactly `data_set_ids` -- no more, no less, and never anything implicit
        on a dataset that isn't listed.
        """
        for dataset in get_objects_for_user(service_account, PERM_VIEW_DATASET):
            remove_all_dataset_grants(service_account, dataset)
        for dataset in DataSet.objects.filter(pk__in=data_set_ids):
            for permission in permissions:
                assign_perm(f"{permission.content_type.app_label}.{permission.codename}", service_account, dataset)


class ServiceAccountSerializer(serializers.ModelSerializer):
    data_set_ids = serializers.SerializerMethodField()
    is_admin = serializers.BooleanField(read_only=True)
    permission_ids = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "date_joined", "data_set_ids", "is_active", "is_admin", "permission_ids"]

    def get_data_set_ids(self, obj):
        return list(get_objects_for_user(obj, PERM_VIEW_DATASET).values_list("id", flat=True))

    def get_permission_ids(self, obj):
        """The dataset-scoped permission_ids currently granted -- derived from the first
        assigned dataset's actual grants (by construction, every listed dataset holds the same
        set, since _sync_data_sets applies them uniformly)."""
        if obj.is_admin:
            return []
        dataset_ids = self.get_data_set_ids(obj)
        if not dataset_ids:
            return []
        first_dataset = DataSet.objects.get(pk=dataset_ids[0])
        held_bare_codenames = [
            codename.split(".")[-1] for codename in DATASET_PERMISSION_CODENAMES if obj.has_perm(codename, first_dataset)
        ]
        return list(
            Permission.objects.filter(
                content_type__app_label="catalog", codename__in=held_bare_codenames
            ).values_list("id", flat=True)
        )


class TokenResponseSerializer(serializers.Serializer):
    token = serializers.CharField()


class AvailabilityResponseSerializer(serializers.Serializer):
    is_available = serializers.BooleanField()


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]


_GLOBAL_PERMISSION_BARE_CODENAMES = {c.split(".")[-1] for c in GLOBAL_PERMISSION_CODENAMES}


class GroupDetailSerializer(serializers.ModelSerializer):
    permission_ids = serializers.PrimaryKeyRelatedField(
        source="permissions",
        many=True,
        queryset=Permission.objects.filter(codename__in=_GLOBAL_PERMISSION_BARE_CODENAMES),
    )
    is_system = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "name", "permission_ids", "is_system"]

    def get_is_system(self, obj):
        return obj.name == ADMIN_GROUP_NAME

    def validate_name(self, value):
        if self.instance and self.instance.name == ADMIN_GROUP_NAME and value != ADMIN_GROUP_NAME:
            raise serializers.ValidationError("The Admin group cannot be renamed.")
        return value


class GroupMemberSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    is_service_account = serializers.BooleanField()


class DatasetRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetRole
        fields = ["id", "name", "is_system"]


class DatasetRoleDetailSerializer(serializers.ModelSerializer):
    permission_ids = serializers.PrimaryKeyRelatedField(
        source="permissions",
        many=True,
        queryset=Permission.objects.filter(codename__in=_DATASET_PERMISSION_BARE_CODENAMES),
    )

    class Meta:
        model = DatasetRole
        fields = ["id", "name", "permission_ids", "is_system"]
        read_only_fields = ["is_system"]


class PermissionOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    codename = serializers.SerializerMethodField()
    name = serializers.CharField()
    description = serializers.SerializerMethodField()
    implies = serializers.SerializerMethodField()

    def get_codename(self, obj):
        return f"{obj.content_type.app_label}.{obj.codename}"

    def get_description(self, obj):
        entry = getattr(obj, "description_entry", None)
        return entry.description if entry else ""

    def get_implies(self, obj):
        """The codename of the view permission this one implies (e.g. manage_users implies
        view_users), or None -- the single source of truth for the composer's auto-check
        behavior, set via PermissionDescription.implied_view_permission."""
        entry = getattr(obj, "description_entry", None)
        implied = entry.implied_view_permission if entry else None
        return f"{implied.content_type.app_label}.{implied.codename}" if implied else None
