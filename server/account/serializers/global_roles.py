from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from account.models import GlobalRole

from .permissions import GrantedPermissionsMixin, PermissionCodeField


class GlobalRoleSerializer(serializers.ModelSerializer):
    """A global role in a listing, or nested inside a dataset role assignment."""

    class Meta:
        model = GlobalRole
        fields = ["id", "name", "description"]


class GlobalRoleDetailSerializer(GrantedPermissionsMixin, serializers.ModelSerializer):
    permissions = PermissionCodeField(many=True, required=False)

    class Meta:
        model = GlobalRole
        fields = ["id", "name", "description", "permissions"]
        extra_kwargs = {
            "name": {
                "validators": [
                    UniqueValidator(
                        queryset=GlobalRole.objects.all(),
                        message="A global role with this name already exists.",
                    )
                ]
            }
        }


class GlobalRoleReferenceSerializer(serializers.Serializer):
    """A request body that names a global role."""

    global_role_id = serializers.PrimaryKeyRelatedField(source="global_role", queryset=GlobalRole.objects.all())
