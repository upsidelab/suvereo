from django.contrib.auth.models import Group
from rest_framework import serializers

from .permissions import GrantedPermissionsMixin, PermissionCodeField


class GroupSerializer(serializers.ModelSerializer):
    """A group in a listing, or nested inside a role assignment."""

    class Meta:
        model = Group
        fields = ["id", "name"]


class GroupDetailSerializer(GrantedPermissionsMixin, serializers.ModelSerializer):
    permissions = PermissionCodeField(many=True, required=False)

    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]


class GroupReferenceSerializer(serializers.Serializer):
    """A request body that names a group."""

    group_id = serializers.PrimaryKeyRelatedField(source="group", queryset=Group.objects.all())
