from enthusiast_common.integrations import BaseIntegration

from catalog.integrations.registry import IntegrationManagerRegistry
from catalog.models import Integration


class IntegrationSyncService:
    """Pulls an integration's data into its DataSet through its category's manager."""

    def sync(self, plugin: BaseIntegration, integration: Integration) -> bool:
        """Pull a plugin's data into the DataSet its integration belongs to.

        Args:
            plugin: A configured plugin instance; it need not be one the plugin registry knows.
            integration: The stored record the synced data is attributed to.

        Returns:
            False when no manager pulls data for this kind of integration, True otherwise.
        """
        manager = IntegrationManagerRegistry().get_manager_for(type(plugin).INTEGRATION_MANAGER)
        if manager is None:
            return False
        manager.sync(plugin, integration.dataset_id, integration.id)
        return True
