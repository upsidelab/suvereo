from celery import shared_task

from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.integrations.sync_service import IntegrationSyncService
from catalog.models import Integration
from catalog.task_status.task_types import CatalogTaskType


@shared_task
def sync_integration_task(integration_id: int):
    integration = Integration.objects.get(pk=integration_id)
    synced = IntegrationSyncService().sync(IntegrationPluginRegistry().build_instance(integration), integration)
    return {
        "task_type": CatalogTaskType.INTEGRATION_SYNC,
        "integration_id": integration.id,
        "data_set_id": integration.dataset_id,
        "synced": synced,
    }
