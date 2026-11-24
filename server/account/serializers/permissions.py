from django.contrib.auth.models import Permission
from django.core.exceptions import ImproperlyConfigured
from rest_framework import serializers

from account.authorization import (
    GLOBAL_SCOPE_PERMISSIONS,
    INTERNAL_CODES,
    PUBLIC_CODES,
    missing_dependencies,
    permission_label,
)


class PermissionOptionSerializer(serializers.Serializer):
    code = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    requires = serializers.ListField(child=serializers.CharField(), read_only=True)


class PermissionEntitySerializer(serializers.Serializer):
    entity = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    permissions = PermissionOptionSerializer(many=True, read_only=True)


class PermissionCodeField(serializers.RelatedField):
    queryset = Permission.objects.select_related("content_type")

    def to_representation(self, permission) -> str:
        label = permission_label(permission)
        try:
            return PUBLIC_CODES[label]
        except KeyError:
            raise ImproperlyConfigured(f"Permission {label} is in the database but is not declared in PERMISSIONS.") from None

    def to_internal_value(self, code) -> Permission:
        codename = INTERNAL_CODES.get(code)
        if codename is None:
            raise serializers.ValidationError(f"Unknown permission: {code}.")
        app_label, bare_codename = codename.split(".")
        try:
            return self.get_queryset().get(content_type__app_label=app_label, codename=bare_codename)
        except Permission.DoesNotExist:
            raise serializers.ValidationError(f"Permission {code} is declared but missing from the database.") from None


class GrantedPermissionsMixin:
    grantable_permissions: list[str] = GLOBAL_SCOPE_PERMISSIONS
    not_grantable_error = "Cannot be granted here: {codes}."

    def validate_permissions(self, permissions):
        granted = {permission_label(permission) for permission in permissions}

        not_grantable = sorted(PUBLIC_CODES[codename] for codename in granted - set(self.grantable_permissions))
        if not_grantable:
            raise serializers.ValidationError(self.not_grantable_error.format(codes=", ".join(not_grantable)))
        return permissions

    def validate(self, attrs):
        if "permissions" in attrs:
            missing = self._missing_dependencies(attrs["permissions"])
            if missing:
                raise serializers.ValidationError(
                    {
                        "permissions": [
                            f"{entry['code']} is required by {', '.join(entry['required_by'])}." for entry in missing
                        ],
                        "missing_permissions": missing,
                    }
                )
        return super().validate(attrs)

    def _missing_dependencies(self, permissions) -> list[dict]:
        granted = {permission_label(permission) for permission in permissions}
        return missing_dependencies(granted, self.grantable_permissions)
