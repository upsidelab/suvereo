from celery import shared_task

from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.models import Integration


@shared_task
def sync_integration_task(integration_id: int):
    integration = Integration.objects.get(pk=integration_id)
    plugin = IntegrationPluginRegistry().build_instance(integration)
    plugin.sync(integration.dataset_id)
