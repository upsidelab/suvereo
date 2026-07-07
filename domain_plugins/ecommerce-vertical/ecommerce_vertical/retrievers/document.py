from django.db.models import QuerySet
from pgvector.django import CosineDistance

from agent.core.registries.embeddings import EmbeddingProviderRegistry
from catalog.models import DataSet
from ecommerce_vertical.models import DocumentChunk


class DocumentRetriever:
    """Retrieves document chunks from the vertical's DocumentChunk table using vector similarity."""

    def __init__(self, data_set_id: int, max_results: int = 12):
        self.data_set_id = data_set_id
        self.max_results = max_results

    def find_content_matching_query(self, query: str) -> QuerySet[DocumentChunk]:
        embedding_vector = self._create_embedding_for_query(query)
        relevant_documents = self._find_documents_matching_vector(embedding_vector)
        return relevant_documents

    def _create_embedding_for_query(self, query: str) -> list[float]:
        data_set = DataSet.objects.get(id=self.data_set_id)
        embedding_provider = EmbeddingProviderRegistry().provider_for_dataset(self.data_set_id)
        return embedding_provider(data_set.embedding_model, data_set.embedding_vector_dimensions).generate_embeddings(
            query
        )

    def _find_documents_matching_vector(self, embedding_vector: list[float]) -> QuerySet[DocumentChunk]:
        embedding_distance = CosineDistance("embedding", embedding_vector)
        matching_documents = DocumentChunk.objects.filter(document__dataset_id=self.data_set_id).order_by(
            embedding_distance
        )
        limited_matching_documents = matching_documents[: self.max_results]
        return limited_matching_documents
