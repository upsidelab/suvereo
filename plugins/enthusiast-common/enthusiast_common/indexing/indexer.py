from abc import ABC, abstractmethod

from .protocols import IndexableEntity


class BaseEntityIndexer(ABC):
    """Indexes a domain entity's content for vector search.

    Implementations chunk ``entity.get_indexable_content()``, embed each chunk,
    and persist the vectors to the entity's chunk table (a ``BaseEmbeddingChunk``
    subclass). The framework host provides a concrete implementation and injects
    it into source integration managers, so plugin packages depend only on this
    interface. See ``IndexableEntity`` for the contract the entity must satisfy.
    """

    @abstractmethod
    def index(self, entity: IndexableEntity) -> None:
        """Chunk, embed, and store the entity's indexable content."""
