from django.contrib.auth.models import Group
from django.db import models

from .dataset_role import DatasetRole


class DatasetGlobalRoleAssignment(models.Model):
    """A dataset role held on one data set by everyone in one global role."""

    global_role = models.ForeignKey(Group, on_delete=models.CASCADE)
    dataset = models.ForeignKey("catalog.DataSet", on_delete=models.CASCADE)
    role = models.ForeignKey(DatasetRole, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("global_role", "dataset", "role")

    def __str__(self):
        return f"{self.global_role} — {self.role} @ {self.dataset}"
