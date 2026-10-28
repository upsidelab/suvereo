from typing import List, Type

from django.conf import settings
from suvereo_common.integrations import BaseIntegration, BaseOAuthIntegration
from utils.base_registry import BaseRegistry

from catalog.integrations.config_patch import config_writer_for
from catalog.models import Integration


class IntegrationPluginRegistry(BaseRegistry[BaseIntegration]):
    """Resolves integration plugin classes registered in CATALOG_INTEGRATION_PLUGINS."""

    plugin_base = BaseIntegration

    def get_plugin_classes(self) -> List[Type[BaseIntegration]]:
        return [self._get_plugin_class_by_path(path) for path in settings.CATALOG_INTEGRATION_PLUGINS]

    def _classes_by_type(self) -> dict[str, Type[BaseIntegration]]:
        return {cls.TYPE: cls for cls in self.get_plugin_classes()}

    def get_plugin_class_by_type(self, integration_type: str) -> Type[BaseIntegration]:
        try:
            return self._classes_by_type()[integration_type]
        except KeyError:
            raise KeyError(f"No integration plugin registered with TYPE='{integration_type}'.")

    def build_instance(self, integration: Integration) -> BaseIntegration:
        """Instantiate the plugin for a stored Integration record, with its config on self."""
        plugin = self.get_plugin_class_by_type(integration.type)()
        if integration.config:
            plugin.set_runtime_arguments({"configuration_args": integration.config})
        if isinstance(plugin, BaseOAuthIntegration):
            plugin.set_config_writer(config_writer_for(integration.pk))
        return plugin
