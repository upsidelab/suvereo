"""Writing back config an integration renewed for itself."""

from typing import Any, Awaitable, Callable

from asgiref.sync import sync_to_async
from django.db import transaction

from catalog.models import DataSet, Integration


def merge_into_integration(integration_id: Any, patch: dict[str, Any], dataset: DataSet | None = None) -> None:
    """Merge `patch` into one integration's stored config, leaving the rest of the record alone.

    Does nothing when no integration matches, so renewing a config that is not saved yet - a token
    being connected in a form that has never been submitted - is not an error.
    """
    if not integration_id:
        return
    with transaction.atomic():
        rows = Integration.objects.select_for_update().filter(pk=integration_id)
        if dataset is not None:
            rows = rows.filter(dataset=dataset)
        row = rows.first()
        if row is None:
            return
        row.config = {**row.config, **patch}
        row.save(update_fields=["config", "updated_at"])


def config_writer_for(integration_id: Any) -> Callable[[dict[str, Any]], Awaitable[None]]:
    """An awaitable writer a plugin instance can call to persist config it renewed mid-conversation."""

    @sync_to_async
    def write(patch: dict[str, Any]) -> None:
        merge_into_integration(integration_id, patch)

    return write
