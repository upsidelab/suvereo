from django.conf import settings
from django.db import models

from .global_role import GlobalRole


class UserGroupQuerySet(models.QuerySet):
    """Adds the counts every group listing displays."""

    def with_counts(self):
        """Annotates member, global role and dataset role counts.

        `distinct=True` on each: needed because of how QuerySet.annotate() works;
        It constructs SQL query with joins. Having multiple annotations on one query
        causes it to produce multiple joins on a query resulting in one row per
        combination of joined rows. Without `distinct=True` the multiple count
        annotations effectively multiply each other.
        """
        return self.annotate(
            member_count=models.Count("members", distinct=True),
            global_role_count=models.Count("global_roles", distinct=True),
            data_set_role_count=models.Count("datasetgrouproleassignment", distinct=True),
        )


class UserGroup(models.Model):
    """A named bucket of users, published as `group` throughout the API.

    Holds subjects and nothing else. A group is granted a global role, or a dataset role on a
    data set, or both; its members hold everything the group holds. Named `UserGroup` because a
    bare `Group` would read as Django's own retired one; every public surface says `group`.
    """

    objects = UserGroupQuerySet.as_manager()

    name = models.CharField(max_length=150, unique=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="user_groups", blank=True)
    global_roles = models.ManyToManyField(GlobalRole, related_name="holders", blank=True)

    class Meta:
        permissions = [("assign_usergroup", "Add users to and remove them from groups")]

    def __str__(self):
        return self.name
