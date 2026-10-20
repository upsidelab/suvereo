from enthusiast_common.integrations import BaseIntegration

from catalog.integrations.registry import IntegrationManagerRegistry
from catalog.models import Integration


class IntegrationSyncService:
    """Pulls an integration's data into its DataSet through its category's manager."""

    def sync(self, plugin: BaseIntegration, integration: Integration) -> bool:
        """Sync the plugin's data into the integration's DataSet; False when no manager pulls data for it."""
        manager = IntegrationManagerRegistry().get_manager_for(type(plugin).INTEGRATION_MANAGER)
        if manager is None:
            return False
        manager.sync(plugin, integration.dataset_id, integration.id)
        return True
