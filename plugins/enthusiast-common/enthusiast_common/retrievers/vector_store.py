from abc import ABC, abstractmethod
from typing import Any, Generic, Iterable, TypeVar

from enthusiast_common.registry import BaseEmbeddingProviderRegistry
from enthusiast_common.repositories import BaseDataSetRepository, BaseModelChunkRepository

from .base import BaseRetriever

T = TypeVar("T")


class BaseVectorStoreRetriever(BaseRetriever, ABC, Generic[T]):
    def __init__(
        self,
        data_set_id: Any,
        data_set_repo: BaseDataSetRepository,
        model_chunk_repo: BaseModelChunkRepository[T],
        embeddings_registry: BaseEmbeddingProviderRegistry,
        max_objects: int = 12,
    ):
        self.data_set_id = data_set_id
        self.data_set_repo = data_set_repo
        self.embeddings_registry = embeddings_registry
        self.max_objects = max_objects
        self.model_chunk_repo = model_chunk_repo

    @abstractmethod
    def find_content_matching_query(self, query: str) -> Iterable[T]:
        pass

    def _create_embedding_for_query(self, query: str) -> list[float]:
        """Embed a query with the same provider/config that produced the stored vectors."""
        data_set = self.data_set_repo.get_by_id(self.data_set_id)
        provider_class = self.embeddings_registry.provider_for_dataset(self.data_set_id)
        provider = provider_class(data_set.embedding_model, data_set.embedding_vector_dimensions)
        return provider.generate_embeddings(query)
