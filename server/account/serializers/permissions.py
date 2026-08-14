from django.contrib.auth.models import Permission
from rest_framework import serializers

from account.authorization import (
    GLOBAL_SCOPE_PERMISSIONS,
    INTERNAL_CODES,
    PUBLIC_CODES,
    VIEW_DEPENDENCIES,
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
        return PUBLIC_CODES[permission_label(permission)]

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
    2. Granting `add`/`change`/`delete` on an entity requires also granting its `view`. The error
       names the missing code instead of adding it.

    Mixed into the group and dataset-role serializers, which differ only in the allowed set.
    """

    grantable_permissions: list[str] = GLOBAL_SCOPE_PERMISSIONS
    not_grantable_error = "Cannot be granted here: {codes}."

    def validate_permissions(self, permissions):
        granted = {permission_label(permission) for permission in permissions}

        not_grantable = sorted(PUBLIC_CODES[codename] for codename in granted - set(self.grantable_permissions))
        if not_grantable:
            raise serializers.ValidationError(self.not_grantable_error.format(codes=", ".join(not_grantable)))

        unmet = sorted(
            (PUBLIC_CODES[codename], PUBLIC_CODES[VIEW_DEPENDENCIES[codename]])
            for codename in granted
            if codename in VIEW_DEPENDENCIES and VIEW_DEPENDENCIES[codename] not in granted
        )
        if unmet:
            raise serializers.ValidationError(
                [f"Granting {code} also requires {required}." for code, required in unmet]
            )
        return permissions
