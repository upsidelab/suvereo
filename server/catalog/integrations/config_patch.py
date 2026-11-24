from collections.abc import Awaitable, Callable
from typing import Any

from channels.db import database_sync_to_async
from django.db import transaction

from catalog.models import DataSet, Integration


def merge_into_integration(integration_id: Any, patch: dict[str, Any], dataset: DataSet | None = None) -> None:
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
    @database_sync_to_async
    def write(patch: dict[str, Any]) -> None:
        merge_into_integration(integration_id, patch)

    return write
