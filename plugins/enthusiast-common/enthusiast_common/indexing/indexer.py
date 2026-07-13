from abc import ABC, abstractmethod
from typing import Any


class BaseEntityIndexer(ABC):
    """Indexes a domain entity's content for vector search.

    Implementations chunk ``entity.get_indexable_content()``, embed each chunk,
    and persist the vectors to the entity's chunk table. The framework host
    provides a concrete implementation and injects it into source integration
    managers, so plugin packages depend only on this interface.

    The entity must expose:
      - ``dataset`` — the DataSet-like object holding the embedding configuration,
      - ``get_indexable_content() -> str`` — the text to index,
      - ``chunks`` — reverse manager to the entity's ``BaseEmbeddingChunk`` table
        (a foreign key on the chunk model declared with ``related_name="chunks"``).
    """

    @abstractmethod
    def index(self, entity: Any) -> None:
        """Chunk, embed, and store the entity's indexable content."""
