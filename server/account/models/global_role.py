from django.conf import settings
from django.contrib.auth.models import Permission
from django.db import models


class GlobalRole(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.CharField(max_length=255, blank=True, default="")
    permissions = models.ManyToManyField(Permission, blank=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="global_roles", blank=True)

    class Meta:
        permissions = [("assign_globalrole", "Add users to and remove them from global roles")]

    def __str__(self):
        return self.name
