import logging
from typing import Any, Optional, TypeVar

from django.db.models import QuerySet
from pydantic import ValidationError
from suvereo_common.integrations import BaseIntegration, BaseIntegrationPluginResolver

from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.models import Integration

logger = logging.getLogger(__name__)

IntegrationT = TypeVar("IntegrationT", bound=BaseIntegration)


class IntegrationPluginResolver(BaseIntegrationPluginResolver):
    """Resolves a data set's integration plugin from the catalog Integration records."""

    def __init__(self) -> None:
        self._registry = IntegrationPluginRegistry()

    def resolve(self, data_set_id: Any, plugin_base: type[IntegrationT]) -> Optional[IntegrationT]:
        """Return a configured plugin instance of *plugin_base* for the data set, or None.

        When more than one integration matches (a type with ``ALLOWS_MULTIPLE_INSTANCES``, or several
        distinct types under the same *plugin_base* category), the latest-added one wins — never an
        arbitrary one.
        """
        integration = self._matching(data_set_id, plugin_base).order_by("-id").first()
        if integration is None:
            return None
        return self._registry.build_instance(integration)

    def resolve_all_for_agent(self, agent_id: Any, plugin_base: type[IntegrationT]) -> list[IntegrationT]:
        """Return a plugin instance of *plugin_base* for every integration selected for the agent.

        A record whose stored config no longer validates against its plugin's ``CONFIGURATION_ARGS``
        is logged and skipped, so one mis-configured integration cannot take down the others. Callers
        of this method treat the result as best-effort — unlike :meth:`resolve`, which is used where a
        single missing integration should surface as an error.
        """
        instances = []
        for integration in self._matching_for_agent(agent_id, plugin_base):
            try:
                instances.append(self._registry.build_instance(integration))
            except (ValidationError, TypeError):
                logger.warning(
                    "Skipping integration %s (type %s, dataset %s): stored config could not be loaded",
                    integration.id,
                    integration.type,
                    integration.dataset_id,
                    exc_info=True,
                )
        return instances

    def has_any_for_agent(self, agent_id: Any, plugin_base: type[IntegrationT]) -> bool:
        """Return whether at least one integration of *plugin_base* is selected for the agent."""
        return self._matching_for_agent(agent_id, plugin_base).exists()

    def ids_for_data_set(self, data_set_id: Any, plugin_base: type[IntegrationT]) -> list[Any]:
        return list(self._matching(data_set_id, plugin_base).values_list("id", flat=True))

    def _matching(self, data_set_id: Any, plugin_base: type[IntegrationT]) -> QuerySet[Integration]:
        """Integrations on the data set whose plugin class implements *plugin_base*.

        The set of matching types comes from the registry, which reads settings rather than the
        database, so the caller is left with a single query. Records whose type has no registered
        plugin fall outside the filter and are excluded by construction.
        """
        return Integration.objects.filter(dataset_id=data_set_id, type__in=self._types(plugin_base))

    def _matching_for_agent(self, agent_id: Any, plugin_base: type[IntegrationT]) -> QuerySet[Integration]:
        return Integration.objects.filter(agents__id=agent_id, type__in=self._types(plugin_base))

    def _types(self, plugin_base: type[IntegrationT]) -> list[str]:
        return [cls.TYPE for cls in self._registry.get_plugin_classes() if issubclass(cls, plugin_base)]
