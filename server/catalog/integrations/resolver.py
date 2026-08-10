from typing import Any, Optional, TypeVar

from enthusiast_common.integrations import BaseIntegration, BaseIntegrationPluginResolver

from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.models import Integration

IntegrationT = TypeVar("IntegrationT", bound=BaseIntegration)


class CatalogIntegrationPluginResolver(BaseIntegrationPluginResolver):
    """Resolves a data set's integration plugin from the catalog Integration records."""

    def resolve(self, data_set_id: Any, plugin_base: type[IntegrationT]) -> Optional[IntegrationT]:
        """Return a configured  plugin instance of *plugin_base* for the data set, or None.

        When more than one integration matches (a type with ``ALLOWS_MULTIPLE_INSTANCES``, or several
        distinct types under the same *plugin_base* category), the latest-added one wins — never an
        arbitrary one.
        """
        registry = IntegrationPluginRegistry()
        for integration in Integration.objects.filter(dataset_id=data_set_id).order_by("-id"):
            try:
                plugin_class = registry.get_plugin_class_by_type(integration.type)
            except KeyError:
                continue
            if issubclass(plugin_class, plugin_base):
                return registry.build_instance(integration)
        return None

    def resolve_all(self, data_set_id: Any, plugin_base: type[IntegrationT]) -> list[IntegrationT]:
        """Return every configured plugin instance of *plugin_base* for the data set."""
        registry = IntegrationPluginRegistry()
        instances = []
        for integration in Integration.objects.filter(dataset_id=data_set_id):
            try:
                plugin_class = registry.get_plugin_class_by_type(integration.type)
            except KeyError:
                continue
            if issubclass(plugin_class, plugin_base):
                instances.append(registry.build_instance(integration))
        return instances
