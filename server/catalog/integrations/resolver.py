from typing import Any, Optional, TypeVar

from enthusiast_common.integrations import BaseIntegration, BaseIntegrationPluginResolver

from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.models import Integration

IntegrationT = TypeVar("IntegrationT", bound=BaseIntegration)


class CatalogIntegrationPluginResolver(BaseIntegrationPluginResolver):
    """Resolves a data set's integration plugin from the catalog Integration records."""

    def resolve(self, data_set_id: Any, plugin_base: type[IntegrationT]) -> Optional[IntegrationT]:
        """Return a configured plugin instance of *plugin_base* for the data set, or None."""
        registry = IntegrationPluginRegistry()
        for integration in Integration.objects.filter(dataset_id=data_set_id):
            plugin_class = registry.get_plugin_class_by_type(integration.type)
            if issubclass(plugin_class, plugin_base):
                return registry.build_instance(integration)
        return None
