import logging
from typing import Any, Optional, TypeVar

from enthusiast_common.integrations import BaseIntegration, BaseIntegrationPluginResolver

from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.models import Integration

logger = logging.getLogger(__name__)

IntegrationT = TypeVar("IntegrationT", bound=BaseIntegration)


class IntegrationPluginResolver(BaseIntegrationPluginResolver):
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
        """Return every configured plugin instance of *plugin_base* for the data set.

        A record whose stored config no longer validates against its plugin's ``CONFIGURATION_ARGS``
        is logged and skipped, so one mis-configured integration cannot take down the others. Callers
        of this method treat the result as best-effort — unlike :meth:`resolve`, which is used where a
        single missing integration should surface as an error.
        """
        registry = IntegrationPluginRegistry()
        instances = []
        for integration in Integration.objects.filter(dataset_id=data_set_id):
            try:
                plugin_class = registry.get_plugin_class_by_type(integration.type)
            except KeyError:
                continue
            if not issubclass(plugin_class, plugin_base):
                continue
            try:
                instances.append(registry.build_instance(integration))
            except Exception:
                logger.warning(
                    "Skipping integration %s (type %s, dataset %s): stored config could not be loaded",
                    integration.id,
                    integration.type,
                    data_set_id,
                    exc_info=True,
                )
        return instances

    def has_any(self, data_set_id: Any, plugin_base: type[IntegrationT]) -> bool:
        """Return whether the data set has at least one integration of *plugin_base*."""
        registry = IntegrationPluginRegistry()
        types = Integration.objects.filter(dataset_id=data_set_id).values_list("type", flat=True).distinct()
        for integration_type in types:
            try:
                plugin_class = registry.get_plugin_class_by_type(integration_type)
            except KeyError:
                continue
            if issubclass(plugin_class, plugin_base):
                return True
        return False
