from django.conf import settings
from enthusiast_common.integrations import BaseIntegrationType, BaseSourceIntegrationType
from utils.base_registry import BaseRegistry


class IntegrationTypeRegistry(BaseRegistry[BaseIntegrationType]):
    """Reads integration types and sync managers declared in settings.

    CATALOG_INTEGRATION_TYPES  — all known integration type classes (for FE discovery).
    CATALOG_SYNC_MANAGERS      — sync manager classes for types that move data.
    """

    plugin_base = BaseIntegrationType

    def get_all_types(self) -> list[type[BaseIntegrationType]]:
        """Return all registered integration type classes."""
        return [self._get_plugin_class_by_path(path) for path in getattr(settings, "CATALOG_INTEGRATION_TYPES", [])]

    def get_manager_for(self, integration_type: type | None) -> BaseSourceIntegrationType | None:
        """Return an instantiated sync manager for *integration_type*, or None."""
        if integration_type is None:
            return None
        for path in getattr(settings, "CATALOG_SYNC_MANAGERS", []):
            manager_cls = self._get_class_by_path(path, BaseSourceIntegrationType)
            if manager_cls.HANDLES_TYPE is integration_type:
                return manager_cls()
        return None
