from abc import ABC, abstractmethod
from typing import Any

from django.db import models
from pgvector.django import VectorField


class BaseEmbeddingChunk(models.Model):
    """Abstract chunk model: one piece of a domain entity's content plus its embedding.

    A plugin's concrete chunk model inherits this and adds a foreign key to the
    domain model it chunks (with ``related_name="chunks"``). Keeping the chunk
    table on the plugin side lets vector search filter on the domain model's fields.
    """

    content = models.TextField()
    embedding = VectorField(null=True)

    class Meta:
        abstract = True

    def set_embedding(self, embedding_vector: list[float]) -> None:
        """Store a computed embedding vector on this chunk instance."""
        self.embedding = embedding_vector


class BaseEntityIndexer(ABC):
    """Indexes a domain entity's content for vector search.

    Implementations chunk ``entity.get_indexable_content()``, embed each chunk,
    and persist the vectors to the entity's chunk table (a ``BaseEmbeddingChunk``
    subclass). The framework host provides a concrete implementation and injects
    it into source integration managers, so plugin packages depend only on this
    interface.

    The entity must expose:
      - ``dataset`` — the DataSet-like object holding the embedding configuration,
      - ``get_indexable_content() -> str`` — the text to index,
      - ``chunks`` — reverse manager to the entity's ``BaseEmbeddingChunk`` table
        (a foreign key on the chunk model declared with ``related_name="chunks"``).
    """

    @abstractmethod
    def index(self, entity: Any) -> None:
        """Chunk, embed, and store the entity's indexable content."""
