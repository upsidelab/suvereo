from django.db import models

from enthusiast_common.indexing import BaseEmbeddingChunk


class ProductContentChunk(BaseEmbeddingChunk):
    """A tokenised chunk of a Product's indexable content, with its embedding vector."""

    product = models.ForeignKey(
        "ecommerce_vertical.Product",
        on_delete=models.CASCADE,
        related_name="chunks",
    )

