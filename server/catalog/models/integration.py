from django.db import models
from django.db.models import Q

from .data_set import DataSet

#: Name of the partial unique constraint below. Callers that need to tell "this type is already
#: configured" apart from any other integrity failure match on it, so it lives here rather than
#: being spelled out again at the point of the check.
UNIQUE_INTEGRATION_TYPE_CONSTRAINT = "unique_integration_type_per_dataset"


class Integration(models.Model):
    """One connection to an external system, configured on a DataSet.

    The ``type`` matches a registered plugin's ``BaseIntegration.TYPE``; ``config`` holds
    that plugin's stored settings. A DataSet holds at most one integration of a given type,
    unless that type's plugin declares ``ALLOWS_MULTIPLE_INSTANCES``.
    """

    dataset = models.ForeignKey(DataSet, on_delete=models.CASCADE, related_name="integrations")
    type = models.CharField(max_length=128)
    config = models.JSONField(default=dict, blank=True)
    allows_multiple_instances = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "type"],
                condition=Q(allows_multiple_instances=False),
                name=UNIQUE_INTEGRATION_TYPE_CONSTRAINT,
            )
        ]

    def __str__(self):
        return f"{self.type} on dataset {self.dataset_id}"
