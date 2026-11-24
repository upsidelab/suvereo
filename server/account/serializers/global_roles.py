from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from account.models import GlobalRole
from account.serializers.permissions import GrantedPermissionsMixin, PermissionCodeField


class GlobalRoleSerializer(serializers.ModelSerializer):
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
    global_role_id = serializers.PrimaryKeyRelatedField(source="global_role", queryset=GlobalRole.objects.all())
