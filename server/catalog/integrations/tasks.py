from celery import shared_task

from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.integrations.sync_service import IntegrationSyncService
from catalog.models import Integration


@shared_task
def sync_integration_task(integration_id: int):
    integration = Integration.objects.get(pk=integration_id)
    IntegrationSyncService().sync(IntegrationPluginRegistry().build_instance(integration), integration)
