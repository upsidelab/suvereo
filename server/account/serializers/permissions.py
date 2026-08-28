from django.contrib.auth.models import Permission
from django.core.exceptions import ImproperlyConfigured
from rest_framework import serializers

from account.authorization import (
    GLOBAL_SCOPE_PERMISSIONS,
    INTERNAL_CODES,
    PUBLIC_CODES,
    dependencies_within,
    permission_label,
)


class PermissionOptionSerializer(serializers.Serializer):
    """One checkbox in the role editor."""

    code = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)


class PermissionEntitySerializer(serializers.Serializer):
    """The permissions of one entity, which is how the role editor groups its checkboxes."""

    entity = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    permissions = PermissionOptionSerializer(many=True, read_only=True)


class PermissionCodeField(serializers.RelatedField):
    """Represents a `Permission` by its public code (`dataset.add`) rather than by its row id."""

    queryset = Permission.objects.select_related("content_type")

    def to_representation(self, permission) -> str:
        label = permission_label(permission)
        try:
            return PUBLIC_CODES[label]
        except KeyError:
            raise ImproperlyConfigured(f"Permission {label} is in the database but is not declared in PERMISSIONS.")

    def to_internal_value(self, code) -> Permission:
        codename = INTERNAL_CODES.get(code)
        if codename is None:
            raise serializers.ValidationError(f"Unknown permission: {code}.")
        app_label, bare_codename = codename.split(".")
        try:
            return self.get_queryset().get(content_type__app_label=app_label, codename=bare_codename)
        except Permission.DoesNotExist:
            raise serializers.ValidationError(f"Permission {code} is declared but missing from the database.")


class GrantedPermissionsMixin:
    """Validates a set of permissions being granted in one save.

    Two rules, both rejecting rather than silently correcting, so the stored grant only ever
    reflects what an admin explicitly ticked:

    1. Only permissions this kind of grant can actually carry. One outside the set is inert once
       stored - nothing would ever read it - so accepting it would misreport what the grant does.
    2. Every dependency in `PERMISSION_DEPENDENCIES` that applies in this scope is satisfied. The
       error names each missing requirement together with the permissions that made it necessary,
       so the admin can see what they were about to agree to rather than what to type next.

    Nothing is auto-added: a silent grant hides what was actually decided from whoever reads the
    stored set later, while a rejection forces the box to be ticked deliberately.

    Mixed into the group and dataset-role serializers, which differ only in the allowed set.
    """

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

        unmet = [
            {
                "code": PUBLIC_CODES[required],
                "required_by": sorted(PUBLIC_CODES[dependent] for dependent in dependents if dependent in granted),
            }
            for required, dependents in dependencies_within(self.grantable_permissions).items()
            if required not in granted
        ]
        return sorted((entry for entry in unmet if entry["required_by"]), key=lambda entry: entry["code"])
