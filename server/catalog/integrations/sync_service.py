from suvereo_common.integrations import BaseIntegration

from catalog.integrations.registry import IntegrationManagerRegistry
from catalog.models import Integration


class IntegrationSyncService:
    def sync(self, plugin: BaseIntegration, integration: Integration) -> bool:
        manager = IntegrationManagerRegistry().get_manager_for(type(plugin).INTEGRATION_MANAGER)
        if manager is None:
            return False
        manager.sync(plugin, integration.dataset_id, integration.id)
        return True
