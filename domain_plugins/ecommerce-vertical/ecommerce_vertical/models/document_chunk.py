from django.db import models
from enthusiast_common.indexing import BaseEmbeddingChunk


class DocumentChunk(BaseEmbeddingChunk):
    """A tokenised chunk of a Document's content, with its embedding vector."""

    document = models.ForeignKey(
        "ecommerce_vertical.Document",
        on_delete=models.CASCADE,
        related_name="chunks",
    )

