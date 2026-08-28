from django.contrib.auth.models import Group
from django.db import models

from .dataset_role import DatasetRole


class DatasetGroupRoleAssignment(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    dataset = models.ForeignKey("catalog.DataSet", on_delete=models.CASCADE)
    role = models.ForeignKey(DatasetRole, on_delete=models.PROTECT)

    class Meta:
        unique_together = ("group", "dataset", "role")

    def __str__(self):
        return f"{self.group} — {self.role} @ {self.dataset}"
