from django.conf import settings
from suvereo_common.integrations import BaseSourceIntegrationManager
from utils.base_registry import BaseRegistry

from agent.core.registries.embeddings import EmbeddingProviderRegistry
from catalog.indexing.pipeline import EmbeddingIndexer


class IntegrationManagerRegistry(BaseRegistry[BaseSourceIntegrationManager]):
    plugin_base = BaseSourceIntegrationManager

    def get_manager_for(self, integration_manager: type | None) -> BaseSourceIntegrationManager | None:
        if integration_manager is None:
            return None
        for path in getattr(settings, "CATALOG_INTEGRATION_MANAGERS", []):
            manager_cls = self._get_class_by_path(path, BaseSourceIntegrationManager)
            if issubclass(manager_cls, integration_manager):
                return manager_cls(indexer=EmbeddingIndexer(EmbeddingProviderRegistry()))
        return None
