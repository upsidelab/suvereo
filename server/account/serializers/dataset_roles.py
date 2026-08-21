from rest_framework import serializers

from account.authorization import DATASET_SCOPE_PERMISSIONS
from account.models import DatasetGlobalRoleAssignment, DatasetRole, DatasetUserRoleAssignment

from .global_roles import GlobalRoleSerializer
from .permissions import GrantedPermissionsMixin, PermissionCodeField
from .users import UserSummarySerializer


class DatasetRoleSerializer(serializers.ModelSerializer):
    """A role in a listing, or nested inside an assignment."""

    class Meta:
        model = DatasetRole
        fields = ["id", "name"]


class DatasetRoleDetailSerializer(GrantedPermissionsMixin, serializers.ModelSerializer):
    permissions = PermissionCodeField(many=True, required=False)

    grantable_permissions = DATASET_SCOPE_PERMISSIONS
    not_grantable_error = (
        "A dataset role can only carry dataset-scoped permissions, so these cannot be granted on one: {codes}."
    )

    class Meta:
        model = DatasetRole
        fields = ["id", "name", "permissions"]


class DatasetUserRoleAssignmentSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    role = DatasetRoleSerializer(read_only=True)

    class Meta:
        model = DatasetUserRoleAssignment
        fields = ["id", "user", "role"]


class DatasetGlobalRoleAssignmentSerializer(serializers.ModelSerializer):
    global_role = GlobalRoleSerializer(read_only=True)
    role = DatasetRoleSerializer(read_only=True)

    class Meta:
        model = DatasetGlobalRoleAssignment
        fields = ["id", "global_role", "role"]
