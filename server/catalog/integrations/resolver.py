from typing import Any, Optional

from enthusiast_common.integrations import BaseIntegration, BaseIntegrationPluginResolver

from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.models import Integration


class CatalogIntegrationPluginResolver(BaseIntegrationPluginResolver):
    """Resolves a data set's integration plugin from the catalog Integration records."""

    def resolve(self, data_set_id: Any, plugin_base: type) -> Optional[BaseIntegration]:
        """Return a configured plugin instance of *plugin_base* for the data set, or None."""
        for integration in Integration.objects.filter(dataset_id=data_set_id):
            plugin_class = IntegrationPluginRegistry().get_plugin_class_by_type(integration.type)
            if issubclass(plugin_class, plugin_base):
                plugin = plugin_class()
                if integration.config:
                    plugin.set_runtime_arguments({"configuration_args": integration.config})
                return plugin
        return None
