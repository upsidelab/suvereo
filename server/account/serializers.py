from django.contrib.auth.models import Group, Permission
from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers

from account.authorization import (
    ADMIN_GROUP_NAME,
    DATASET_PERMISSION_CODENAMES,
    GLOBAL_PERMISSION_CODENAMES,
    PERM_VIEW_DATASET,
    assert_group_ids_assignable,
    assert_not_self_removing_from_admin,
    assert_user_deactivatable,
    grant_full_dataset_access,
    is_application_admin,
    remove_all_dataset_grants,
)
from account.models import DatasetRole, User
from catalog.models import DataSet

from .services import ServiceAccountNameService


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


class CreateUpdateServiceAccountSerializer(GroupAssignmentValidationMixin, serializers.Serializer):
    name = serializers.CharField(write_only=True)
    is_active = serializers.BooleanField(default=True)
    group_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    data_set_ids = serializers.ListField(child=serializers.IntegerField(), required=False)

    def validate(self, attrs):
        request = self.context.get("request")
        if request is not None and self.instance is not None and attrs.get("is_active") is False:
            assert_user_deactivatable(request.user, self.instance)
        return attrs

    def create(self, validated_data):
        email = self._build_service_account_email(validated_data.get("name"))
        service_account = User.objects.create_service_account(
            email=email, is_active=validated_data.get("is_active")
        )
        service_account.groups.set(Group.objects.filter(pk__in=validated_data.get("group_ids", [])))
        self._sync_data_sets(service_account, validated_data.get("data_set_ids", []))
        return service_account

    def update(self, instance, validated_data):
        instance.email = self._build_service_account_email(validated_data.get("name"))
        instance.is_active = validated_data.get("is_active")
        instance.save()
        if "group_ids" in validated_data:
            instance.groups.set(Group.objects.filter(pk__in=validated_data["group_ids"]))
        self._sync_data_sets(instance, validated_data.get("data_set_ids", []))
        return instance

    def _build_service_account_email(self, name):
        service = ServiceAccountNameService()
        return service.generate_service_account_email(name)

    def _sync_data_sets(self, service_account, data_set_ids):
        """Replace every dataset-access grant this service account holds with exactly `data_set_ids`.

        Datasets no longer covered lose all access-role permissions; each requested dataset
        is (re)granted full dataset access directly, preserving the full-access semantics of
        the retired `DataSet.users` M2M, consistent with how the data migration grants regular
        users.
        """
        for dataset in get_objects_for_user(service_account, PERM_VIEW_DATASET):
            remove_all_dataset_grants(service_account, dataset)
        for dataset in DataSet.objects.filter(pk__in=data_set_ids):
            grant_full_dataset_access(service_account, dataset)


class ServiceAccountSerializer(serializers.ModelSerializer):
    data_set_ids = serializers.SerializerMethodField()
    is_admin = serializers.BooleanField(read_only=True)
    group_ids = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "date_joined", "data_set_ids", "is_active", "is_admin", "group_ids"]

    def get_data_set_ids(self, obj):
        return list(get_objects_for_user(obj, PERM_VIEW_DATASET).values_list("id", flat=True))

    def get_group_ids(self, obj):
        return list(obj.groups.values_list("id", flat=True))


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


_DATASET_PERMISSION_BARE_CODENAMES = {c.split(".")[-1] for c in DATASET_PERMISSION_CODENAMES}


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
