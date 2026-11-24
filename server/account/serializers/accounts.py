from rest_framework import serializers

from account.authorization import PUBLIC_CODES


class AccountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    is_admin = serializers.BooleanField(source="is_superuser")
    permissions = serializers.SerializerMethodField()

    def get_permissions(self, user) -> list[str]:
        return sorted(PUBLIC_CODES[codename] for codename in user.get_all_permissions() if codename in PUBLIC_CODES)
