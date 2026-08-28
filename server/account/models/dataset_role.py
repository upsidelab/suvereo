from django.contrib.auth.models import Permission
from django.db import models


class DatasetRole(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True, default="")
    permissions = models.ManyToManyField(Permission, blank=True)

    class Meta:
        permissions = [("assign_datasetrole", "Can assign dataset roles to users and groups")]

    def __str__(self):
        return self.name
