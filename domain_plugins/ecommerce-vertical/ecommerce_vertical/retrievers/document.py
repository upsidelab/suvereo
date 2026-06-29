from typing import Any

from pgvector.django import CosineDistance

from ecommerce_vertical.models import DocumentChunk


class DocumentRetriever:
    """Retrieves document chunks from the vertical's DocumentChunk table using vector similarity."""

    def __init__(self, data_set_id: Any, max_results: int = 12):
        self.data_set_id = data_set_id
        self.max_results = max_results

    def _embed_query(self, query: str) -> list[float]:
        from django.apps import apps

        from agent.core.registries.embeddings import EmbeddingProviderRegistry

        DataSet = apps.get_model("catalog", "DataSet")
        data_set = DataSet.objects.get(pk=self.data_set_id)
        provider_class = EmbeddingProviderRegistry().provider_for_dataset(self.data_set_id)
        provider = provider_class(data_set.embedding_model, data_set.embedding_vector_dimensions)
        return provider.generate_embeddings(query)

    def find_content_matching_query(self, query: str) -> list:
        """Return DocumentChunk instances closest to *query* in the dataset."""
        embedding = self._embed_query(query)
        return list(
            DocumentChunk.objects.filter(document__dataset_id=self.data_set_id)
            .order_by(CosineDistance("embedding", embedding))[: self.max_results]
        )
