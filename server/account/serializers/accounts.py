from rest_framework import serializers

from account.authorization import PUBLIC_CODES
from account.models import User


class AccountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    is_admin = serializers.BooleanField(source="is_superuser")
    permissions = serializers.SerializerMethodField()

    def get_permissions(self, user: User) -> list[str]:
        return sorted(PUBLIC_CODES[codename] for codename in user.get_all_permissions() if codename in PUBLIC_CODES)
