from abc import ABC, abstractmethod
from typing import Any, Iterable, TypeVar

T = TypeVar("T")


class BaseSimilaritySearcher(ABC):
    """Performs vector-similarity search against a host-defined chunk table.

    The framework host implements this against its actual vector-search
    technology (e.g. pgvector); ``suvereo-common`` depends only on this
    interface, not on any particular database technology.
    """

    @abstractmethod
    def search(
        self,
        chunk_model: type[T],
        dataset_filter: str,
        data_set_id: Any,
        embedding_vector: list[float],
        max_objects: int,
    ) -> Iterable[T]:
        """Return up to *max_objects* instances of *chunk_model*, ranked by similarity to *embedding_vector*.

        *dataset_filter* is the lookup path from the chunk to its DataSet id
        (e.g. ``"document__dataset_id"``), used to scope results to *data_set_id*.
        """
