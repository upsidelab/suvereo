from typing import Any

from suvereo_common.integrations import BaseToolProvidingIntegration

from agent.core.agents.default_config import get_default_config


class SelectableToolProvidingIntegrations:
    @staticmethod
    def ids(data_set_id: Any) -> list[Any]:
        resolver_class = get_default_config().integration_plugin_resolver
        return resolver_class().ids_for_data_set(data_set_id, BaseToolProvidingIntegration) if resolver_class else []
