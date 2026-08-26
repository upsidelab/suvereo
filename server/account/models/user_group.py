from django.conf import settings
from django.db import models

from .global_role import GlobalRole


class UserGroup(models.Model):
    """A named bucket of users, published as `group` throughout the API.

    Holds subjects and nothing else. A group is granted a global role, or a dataset role on a
    data set, or both; its members hold everything the group holds. Named `UserGroup` because a
    bare `Group` would read as Django's own retired one; every public surface says `group`.
    """

    name = models.CharField(max_length=150, unique=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="user_groups", blank=True)
    global_roles = models.ManyToManyField(GlobalRole, related_name="holders", blank=True)

    class Meta:
        permissions = [("assign_usergroup", "Add users to and remove them from groups")]

    def __str__(self):
        return self.name
