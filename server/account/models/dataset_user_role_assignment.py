from django.conf import settings
from django.db import models

from .dataset_role import DatasetRole


class DatasetUserRoleAssignment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    dataset = models.ForeignKey("catalog.DataSet", on_delete=models.CASCADE)
    role = models.ForeignKey(DatasetRole, on_delete=models.PROTECT)

    class Meta:
        unique_together = ("user", "dataset")

    def __str__(self):
        return f"{self.user} — {self.role} @ {self.dataset}"
