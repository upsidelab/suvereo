from enthusiast_common.integrations import BaseIntegration

from catalog.integrations.registry import IntegrationManagerRegistry
from catalog.models import Integration


class IntegrationSyncService:
    """Pulls an integration's data into its DataSet through the manager of the integration's category."""

    def sync(self, plugin: BaseIntegration, integration: Integration) -> bool:
        """Sync ``plugin``'s data into the DataSet that ``integration`` belongs to.

        Args:
            plugin: A configured plugin instance; it need not be one the plugin registry knows about.
            integration: The stored record the synced data is attributed to.

        Returns:
            Whether a manager took the sync; False for integrations that pull no data.
        """
        manager = IntegrationManagerRegistry().get_manager_for(type(plugin).INTEGRATION_MANAGER)
        if manager is None:
            return False
        manager.sync(plugin, integration.dataset_id, integration.id)
        return True
