from rest_framework import serializers

from account.authorization import PUBLIC_CODES


class AccountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    is_admin = serializers.BooleanField(source="is_superuser")
    permissions = serializers.SerializerMethodField()

    def get_permissions(self, user) -> list[str]:
        """The codes this user holds globally. Filtered through the public vocabulary, which also
        drops the permissions Django and the installed plugins create for their own models - a
        superuser's `get_all_permissions()` returns every row in `auth_permission`, most of which
        this application never checks and has no business publishing."""
        return sorted(PUBLIC_CODES[codename] for codename in user.get_all_permissions() if codename in PUBLIC_CODES)
