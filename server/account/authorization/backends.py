from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission


class RoleBackend(ModelBackend):
    """Authenticates the way Django does; resolves permissions only through global roles."""

    def _get_user_permissions(self, user_obj):
        """Nothing - permissions granted directly to an account are not a supported mechanism."""
        return Permission.objects.none()

    def _get_group_permissions(self, user_obj):
        """The permissions carried by the global roles this account belongs to.

        A group of permissions is `GlobalRole` here, not Django's `auth.Group` - `User.groups` is
        removed from the model, so this is the only thing the name can mean.
        """
        return Permission.objects.filter(globalrole__members=user_obj)
