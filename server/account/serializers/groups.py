from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from account.models import UserGroup

from .global_roles import GlobalRoleSerializer


class GroupSerializer(serializers.ModelSerializer):
    """A group in a listing, with how far what it holds reaches."""

    member_count = serializers.IntegerField(read_only=True, default=0)
    global_role_count = serializers.IntegerField(read_only=True, default=0)
    dataset_role_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = UserGroup
        fields = ["id", "name", "member_count", "global_role_count", "dataset_role_count"]
        extra_kwargs = {
            "name": {
                "validators": [
                    UniqueValidator(
                        queryset=UserGroup.objects.all(),
                        message="A group with this name already exists.",
                    )
                ]
            }
        }


class GroupDetailSerializer(GroupSerializer):
    """A single group, carrying the global roles it holds."""

    global_roles = GlobalRoleSerializer(many=True, read_only=True)

    class Meta(GroupSerializer.Meta):
        fields = [*GroupSerializer.Meta.fields, "global_roles"]
