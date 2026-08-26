from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission
from django.db.models import Q


class RoleBackend(ModelBackend):
    """Authenticates the way Django does; resolves permissions only through global roles."""

    def _get_user_permissions(self, user_obj):
        """Nothing - permissions granted directly to an account are not a supported mechanism."""
        return Permission.objects.none()

    def _get_group_permissions(self, user_obj):
        """The permissions carried by the global roles this account holds - granted to the
        account directly, or to a group (`account.UserGroup`) it belongs to. Never `auth.Group`, which this replaces.
        """
        return Permission.objects.filter(Q(globalrole__members=user_obj) | Q(globalrole__holders__members=user_obj))
