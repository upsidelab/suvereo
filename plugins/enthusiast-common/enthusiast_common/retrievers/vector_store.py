from typing import Any, ClassVar, Generic, TypeVar

from django.db.models import Model, QuerySet
from enthusiast_common.registry import BaseEmbeddingProviderRegistry
from enthusiast_common.repositories import BaseDataSetRepository
from pgvector.django import CosineDistance

from .base import BaseRetriever

T = TypeVar("T", bound=Model)


class BaseVectorStoreRetriever(BaseRetriever, Generic[T]):
    """Vector-similarity retriever over a vertical's embedding chunk table.

    A subclass only declares what is searchable:
      - ``chunk_model`` — the concrete ``BaseEmbeddingChunk`` subclass to query,
      - ``dataset_filter`` — the lookup path from the chunk to its DataSet id
        (e.g. ``"document__dataset_id"``).

    The mechanics are handled here: the query is embedded with the same
    provider/config that produced the stored vectors, and chunks are ranked by
    cosine distance. Override ``find_content_matching_query`` when a vertical
    needs a custom strategy (e.g. an extra lexical filter before the ranking).
    """

    chunk_model: ClassVar[type[Model]]
    dataset_filter: ClassVar[str]

    def __init__(
        self,
        data_set_id: Any,
        data_set_repo: BaseDataSetRepository,
        embeddings_registry: BaseEmbeddingProviderRegistry,
        max_objects: int = 12,
    ):
        self.data_set_id = data_set_id
        self.data_set_repo = data_set_repo
        self.embeddings_registry = embeddings_registry
        self.max_objects = max_objects

    def find_content_matching_query(self, query: str) -> QuerySet[T]:
        """Return up to ``max_objects`` chunks most similar to *query*, best matches first."""
        embedding_vector = self._create_embedding_for_query(query)
        embedding_distance = CosineDistance("embedding", embedding_vector)
        return self.chunk_model.objects.filter(**{self.dataset_filter: self.data_set_id}).order_by(
            embedding_distance
        )[: self.max_objects]

    def _create_embedding_for_query(self, query: str) -> list[float]:
        """Embed a query with the same provider/config that produced the stored vectors."""
        data_set = self.data_set_repo.get_by_id(self.data_set_id)
        provider_class = self.embeddings_registry.provider_for_dataset(self.data_set_id)
        provider = provider_class(data_set.embedding_model, data_set.embedding_vector_dimensions)
        return provider.generate_embeddings(query)
