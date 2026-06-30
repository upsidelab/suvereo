from celery import shared_task

from catalog.integration_type_registry import IntegrationTypeRegistry
from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.models import Integration


@shared_task
def sync_integration_task(integration_id: int):
    integration = Integration.objects.get(pk=integration_id)
    plugin = IntegrationPluginRegistry().build_instance(integration)
    manager = IntegrationTypeRegistry().get_manager_for(getattr(type(plugin), "INTEGRATION_TYPE", None))
    if manager:
        manager.sync(plugin, integration.dataset_id)
