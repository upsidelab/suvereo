from rest_framework import serializers

from account.authorization import DATASET_SCOPE_PERMISSIONS
from account.models import DatasetGroupRoleAssignment, DatasetRole, DatasetUserRoleAssignment

from .groups import GroupSerializer
from .permissions import GrantedPermissionsMixin, PermissionCodeField
from .users import UserSummarySerializer


class DatasetRoleSerializer(serializers.ModelSerializer):
    """A role in a listing, or nested inside an assignment."""

    class Meta:
        model = DatasetRole
        fields = ["id", "name", "description"]


class DatasetRoleDetailSerializer(GrantedPermissionsMixin, serializers.ModelSerializer):
    permissions = PermissionCodeField(many=True, required=False)

    grantable_permissions = DATASET_SCOPE_PERMISSIONS
    not_grantable_error = (
        "A dataset role can only carry dataset-scoped permissions, so these cannot be granted on one: {codes}."
    )

    class Meta:
        model = DatasetRole
        fields = ["id", "name", "description", "permissions"]


class DatasetUserRoleAssignmentSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    role = DatasetRoleSerializer(read_only=True)

    class Meta:
        model = DatasetUserRoleAssignment
        fields = ["id", "user", "role"]


class DatasetGroupRoleAssignmentSerializer(serializers.ModelSerializer):
    group = GroupSerializer(read_only=True)
    role = DatasetRoleSerializer(read_only=True)

    class Meta:
        model = DatasetGroupRoleAssignment
        fields = ["id", "group", "role"]
