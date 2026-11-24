from django.db import models

from account.models.dataset_role import DatasetRole
from account.models.user_group import UserGroup


class DatasetGroupRoleAssignment(models.Model):
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE)
    dataset = models.ForeignKey("catalog.DataSet", on_delete=models.CASCADE)
    role = models.ForeignKey(DatasetRole, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("group", "dataset", "role")

    def __str__(self):
        return f"{self.group} — {self.role} @ {self.dataset}"
