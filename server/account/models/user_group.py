from django.conf import settings
from django.db import models

from account.models.global_role import GlobalRole


class UserGroupQuerySet(models.QuerySet):
    def with_counts(self) -> "UserGroupQuerySet":
        return self.annotate(
            member_count=models.Count("members", distinct=True),
            global_role_count=models.Count("global_roles", distinct=True),
            data_set_role_count=models.Count("datasetgrouproleassignment", distinct=True),
        )


class UserGroup(models.Model):
    objects = UserGroupQuerySet.as_manager()

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, default="")
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="user_groups", blank=True)
    global_roles = models.ManyToManyField(GlobalRole, related_name="holders", blank=True)

    class Meta:
        permissions = [("assign_usergroup", "Add users to and remove them from groups")]

    def __str__(self):
        return self.name
