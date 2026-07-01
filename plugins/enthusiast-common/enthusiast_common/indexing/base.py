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
