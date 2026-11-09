from typing import Any, ClassVar, Generic, Iterable, TypeVar

from suvereo_common.registry import BaseEmbeddingProviderRegistry

from .base import BaseRetriever
from .searcher import BaseSimilaritySearcher

T = TypeVar("T")


class BaseVectorStoreRetriever(BaseRetriever, Generic[T]):
    """Vector-similarity retriever over a domain definition's embedding chunk table.

    A subclass only declares what is searchable:
      - ``chunk_model`` — the concrete ``BaseEmbeddingChunk`` subclass to query,
      - ``dataset_filter`` — the lookup path from the chunk to its DataSet id
        (e.g. ``"document__dataset_id"``).

    The query is embedded with the same provider/config that produced the stored
    vectors; the actual similarity search is delegated to an injected
    ``BaseSimilaritySearcher``, so this class stays free of any database
    technology choice. Override ``find_content_matching_query`` when a domain definition
    needs a custom strategy (e.g. an extra lexical filter before the ranking).
    """

    chunk_model: ClassVar[type]
    dataset_filter: ClassVar[str]

    def __init__(
        self,
        data_set_id: Any,
        embeddings_registry: BaseEmbeddingProviderRegistry,
        searcher: BaseSimilaritySearcher,
        max_objects: int = 12,
    ):
        self.data_set_id = data_set_id
        self.embeddings_registry = embeddings_registry
        self._searcher = searcher
        self.max_objects = max_objects

    def find_content_matching_query(self, query: str) -> Iterable[T]:
        """Return up to ``max_objects`` chunks most similar to *query*, best matches first."""
        embedding_vector = self._create_embedding_for_query(query)
        return self._searcher.search(
            self.chunk_model, self.dataset_filter, self.data_set_id, embedding_vector, self.max_objects
        )

    def _create_embedding_for_query(self, query: str) -> list[float]:
        """Embed a query with the same provider/config that produced the stored vectors."""
        provider = self.embeddings_registry.provider_instance_for_dataset(self.data_set_id)
        return provider.generate_embeddings(query)
