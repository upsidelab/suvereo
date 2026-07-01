from django.conf import settings
from enthusiast_common.integrations import BaseSourceIntegrationManager
from utils.base_registry import BaseRegistry


class IntegrationManagerRegistry(BaseRegistry[BaseSourceIntegrationManager]):
    """Resolves concrete integration manager classes registered in CATALOG_INTEGRATION_MANAGERS."""

    plugin_base = BaseSourceIntegrationManager

    def get_manager_for(self, integration_manager: type | None) -> BaseSourceIntegrationManager | None:
        """Return an instantiated manager whose class is a subclass of *integration_manager*, or None."""
        if integration_manager is None:
            return None
        for path in getattr(settings, "CATALOG_INTEGRATION_MANAGERS", []):
            manager_cls = self._get_class_by_path(path, BaseSourceIntegrationManager)
            if issubclass(manager_cls, integration_manager):
                return manager_cls()
        return None
