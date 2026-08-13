from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from account.models import User

from .services import ServiceAccountNameService


class OnlyAdminsManageAdminsMixin:
    """Restricts admin accounts to admins: a caller who is not an admin can neither grant admin
    nor alter an account that already holds it.

    The second half covers more than revoking and deactivating — editing an admin's email or
    resetting their password would hand over the account just as effectively, so any write
    against an admin target is refused.

    Deliberately keyed off `is_superuser` directly rather than a grantable codename: a
    "may grant admin" permission would let its holder grant it to themselves.
    """

    def validate(self, attrs):
        request = self.context.get("request")
        if request is not None and not request.user.is_superuser:
            if attrs.get("is_superuser"):
                raise PermissionDenied("Only an admin can grant admin access.")
            if self.instance is not None and self.instance.is_superuser:
                raise PermissionDenied("Only an admin can modify an admin account.")
        return super().validate(attrs)


class AccountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    is_admin = serializers.BooleanField(source="is_superuser")
    permissions = serializers.SerializerMethodField()

    def get_permissions(self, user) -> list[str]:
        return sorted(user.get_all_permissions())


class UserSerializer(OnlyAdminsManageAdminsMixin, serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField()
    is_active = serializers.BooleanField()
    is_admin = serializers.BooleanField(source="is_superuser")
    password = serializers.CharField(write_only=True)

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            is_active=validated_data["is_active"],
            is_superuser=validated_data["is_superuser"],
        )


class UserUpdateSerializer(OnlyAdminsManageAdminsMixin, serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField()
    is_active = serializers.BooleanField()
    is_admin = serializers.BooleanField(source="is_superuser")

    def update(self, instance, validated_data):
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        instance.save()
        return instance


class UserUpdatePasswordSerializer(OnlyAdminsManageAdminsMixin, serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    password = serializers.CharField(write_only=True)

    def update(self, instance, validated_data):
        instance.set_password(validated_data["password"])
        instance.save()
        return instance


class CreateUpdateServiceAccountSerializer(OnlyAdminsManageAdminsMixin, serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(write_only=True)
    is_active = serializers.BooleanField(default=True)
    is_admin = serializers.BooleanField(default=False, source="is_superuser")

    def validate_name(self, name):
        if not ServiceAccountNameService().is_service_account_name_available(name, exclude_user=self.instance):
            raise serializers.ValidationError("A service account with this name already exists.")
        return name

    def create(self, validated_data):
        return User.objects.create_service_account(
            email=self._build_service_account_email(validated_data["name"]),
            is_active=validated_data["is_active"],
            is_superuser=validated_data["is_superuser"],
        )

    def update(self, instance, validated_data):
        if "name" in validated_data:
            instance.email = self._build_service_account_email(validated_data.pop("name"))
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        instance.save()
        return instance

    def _build_service_account_email(self, name):
        service = ServiceAccountNameService()
        return service.generate_service_account_email(name)


class ServiceAccountSerializer(serializers.ModelSerializer):
    is_admin = serializers.BooleanField(source="is_superuser")

    class Meta:
        model = User
        fields = ["id", "email", "date_joined", "is_active", "is_admin"]


class TokenResponseSerializer(serializers.Serializer):
    token = serializers.CharField()


class AvailabilityResponseSerializer(serializers.Serializer):
    is_available = serializers.BooleanField()
