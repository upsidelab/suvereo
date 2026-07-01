from celery import shared_task

from catalog.integrations.registry import IntegrationManagerRegistry, IntegrationPluginRegistry
from catalog.models import Integration


@shared_task
def sync_integration_task(integration_id: int):
    integration = Integration.objects.get(pk=integration_id)
    plugin = IntegrationPluginRegistry().build_instance(integration)
    manager = IntegrationManagerRegistry().get_manager_for(getattr(type(plugin), "INTEGRATION_MANAGER", None))
    if manager:
        manager.sync(plugin, integration.dataset_id)
