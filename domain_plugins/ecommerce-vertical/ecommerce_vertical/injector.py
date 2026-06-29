from typing import Any, Optional

from enthusiast_ecommerce_common.connectors import ECommercePlatformConnector

from agent.core.injector import Injector
from ecommerce_vertical.retrievers import DocumentRetriever, ProductRetriever


class EcommerceInjector(Injector):
    """Extends the server Injector with ecommerce-specific retrievers and the platform connector."""

    def __init__(self, *args, data_set_id: Any = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._data_set_id = data_set_id
        self._product_retriever: Optional[ProductRetriever] = None
        self._document_retriever: Optional[DocumentRetriever] = None
        self._ecommerce_platform_connector: Optional[ECommercePlatformConnector] = None

    @property
    def product_retriever(self) -> ProductRetriever:
        if self._product_retriever is None:
            self._product_retriever = ProductRetriever(self._data_set_id)
        return self._product_retriever

    @property
    def document_retriever(self) -> DocumentRetriever:
        if self._document_retriever is None:
            self._document_retriever = DocumentRetriever(self._data_set_id)
        return self._document_retriever

    @property
    def ecommerce_platform_connector(self) -> Optional[ECommercePlatformConnector]:
        """Return the platform connector for this dataset's ecommerce integration, if any."""
        if self._ecommerce_platform_connector is None:
            self._ecommerce_platform_connector = self._build_platform_connector()
        return self._ecommerce_platform_connector

    def _build_platform_connector(self) -> Optional[ECommercePlatformConnector]:
        from enthusiast_ecommerce_common.interfaces import ECommerceIntegrationPlugin

        from catalog.integrations.registry import IntegrationPluginRegistry
        from catalog.models import Integration

        for integration in Integration.objects.filter(dataset_id=self._data_set_id):
            plugin_class = IntegrationPluginRegistry().get_plugin_class_by_type(integration.type)
            if issubclass(plugin_class, ECommerceIntegrationPlugin):
                plugin = plugin_class(config=integration.config)
                return plugin.build_connector()
        return None
