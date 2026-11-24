from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from account.models import UserGroup
from account.serializers.global_roles import GlobalRoleSerializer


class GroupSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True, default=0)
    global_role_count = serializers.IntegerField(read_only=True, default=0)
    data_set_role_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = UserGroup
        fields = ["id", "name", "description", "member_count", "global_role_count", "data_set_role_count"]
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
    global_roles = GlobalRoleSerializer(many=True, read_only=True)

    class Meta(GroupSerializer.Meta):
        fields = [*GroupSerializer.Meta.fields, "global_roles"]


class GroupReferenceSerializer(serializers.Serializer):
    group_id = serializers.PrimaryKeyRelatedField(source="group", queryset=UserGroup.objects.all())
