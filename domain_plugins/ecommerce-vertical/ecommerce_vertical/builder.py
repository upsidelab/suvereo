from typing import Optional

from enthusiast_ecommerce_common.connectors import ECommercePlatformConnector
from enthusiast_ecommerce_common.interfaces import ECommerceIntegrationPlugin

from agent.core.builder import AgentBuilder
from ecommerce_vertical.injector import EcommerceInjector
from ecommerce_vertical.retrievers import DocumentRetriever, ProductRetriever


class EcommerceAgentBuilder(AgentBuilder):
    """AgentBuilder that wires an EcommerceInjector with product and document retrievers."""

    def _build_injector(self) -> EcommerceInjector:
        chat_history = self._build_chat_history()
        memory_compactor = self._build_memory_compactor(chat_history)
        product_retriever = self._build_product_retriever()
        document_retriever = self._build_document_retriever()
        ecommerce_platform_connector = self._build_ecommerce_platform_connector()
        return EcommerceInjector(
            product_retriever=product_retriever,
            document_retriever=document_retriever,
            ecommerce_platform_connector=ecommerce_platform_connector,
            repositories=self._repositories,
            chat_history=chat_history,
            memory_compactor=memory_compactor,
            tool_scratchpad=self._tool_scratchpad,
        )

    def _build_product_retriever(self) -> ProductRetriever:
        return ProductRetriever(data_set_id=self._data_set_id, llm=self._build_default_llm())

    def _build_document_retriever(self) -> DocumentRetriever:
        return DocumentRetriever(
            data_set_id=self._data_set_id,
            embeddings_registry=self._embeddings_registry,
            searcher=self._config.similarity_searcher(),
        )

    def _build_ecommerce_platform_connector(self) -> Optional[ECommercePlatformConnector]:
        from catalog.integrations.registry import IntegrationPluginRegistry
        from catalog.models import Integration

        for integration in Integration.objects.filter(dataset_id=self._data_set_id):
            plugin_class = IntegrationPluginRegistry().get_plugin_class_by_type(integration.type)
            if issubclass(plugin_class, ECommerceIntegrationPlugin):
                plugin: ECommerceIntegrationPlugin = plugin_class()
                if integration.config:
                    plugin.set_runtime_arguments({"configuration_args": integration.config})
                return plugin.build_connector()
        return None
