from django.contrib.auth.models import Group
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .permissions import GrantedPermissionsMixin, PermissionCodeField


class GlobalRoleSerializer(serializers.ModelSerializer):
    """A global role in a listing, or nested inside a dataset role assignment."""

    class Meta:
        model = Group
        fields = ["id", "name"]


class GlobalRoleDetailSerializer(GrantedPermissionsMixin, serializers.ModelSerializer):
    permissions = PermissionCodeField(many=True, required=False)
    # Declared to keep Django's "group" verbose name out of the error, which is API vocabulary.
    name = serializers.CharField(
        max_length=150,
        validators=[
            UniqueValidator(
                queryset=Group.objects.all(),
                message="A global role with this name already exists.",
            )
        ],
    )

    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]


class GlobalRoleReferenceSerializer(serializers.Serializer):
    """A request body that names a global role."""

    global_role_id = serializers.PrimaryKeyRelatedField(source="global_role", queryset=Group.objects.all())
