from pgvector.django import CosineDistance

from agent.core.registries.embeddings import EmbeddingProviderRegistry
from catalog.models import DataSet
from ecommerce_vertical.models import DocumentChunk


class DocumentRetriever:
    """Retrieves document chunks from the vertical's DocumentChunk table using vector similarity."""

    def __init__(self, data_set_id: int, max_results: int = 12):
        self.data_set_id = data_set_id
        self.max_results = max_results

    def find_content_matching_query(self, query: str):
        """Return the DocumentChunks most similar to ``query`` within this DataSet."""
        embedding_vector = self._create_embedding_for_query(query)
        return self._find_documents_matching_vector(embedding_vector)

    def _create_embedding_for_query(self, query: str) -> list[float]:
        """Embed the query with the same provider/config that produced the stored vectors."""
        data_set = DataSet.objects.get(id=self.data_set_id)
        provider_class = EmbeddingProviderRegistry().provider_for_dataset(self.data_set_id)
        provider = provider_class(data_set.embedding_model, data_set.embedding_vector_dimensions)
        return provider.generate_embeddings(query)

    def _find_documents_matching_vector(self, embedding_vector: list[float]):
        """Return the closest chunks to ``embedding_vector`` by cosine distance, limited to max_results."""
        embedding_distance = CosineDistance("embedding", embedding_vector)
        return (
            DocumentChunk.objects.filter(document__dataset_id=self.data_set_id)
            .order_by(embedding_distance)[: self.max_results]
        )
