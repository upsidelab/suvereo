from typing import Any

from django.db import transaction
from langchain_text_splitters import TokenTextSplitter
from suvereo_common.indexing import BaseEntityIndexer, IndexableEntity
from suvereo_common.registry import BaseEmbeddingProviderRegistry, EmbeddingProvider


class EmbeddingIndexer(BaseEntityIndexer):
    """Chunks an entity's indexable content, embeds each chunk, and stores the vectors.

    Splits ``entity.get_indexable_content()`` with the DataSet's token settings, embeds
    each chunk with the DataSet's provider, and writes the chunks to the entity's chunk
    table. Existing chunks are replaced atomically — concurrent calls for the same entity
    are serialised via a row-level lock so no duplicate chunks accumulate.

    See ``BaseEntityIndexer`` for the contract the entity must satisfy.
    """

    def __init__(self, registry: BaseEmbeddingProviderRegistry):
        """Uses registry to resolve the embedding provider configured for the entity's DataSet."""
        self._registry = registry

    def index(self, entity: IndexableEntity) -> None:
        """Chunk, embed, and store the entity's indexable content."""
        data_set = entity.dataset

        splitter = TokenTextSplitter(
            chunk_size=data_set.embedding_chunk_size,
            chunk_overlap=data_set.embedding_chunk_overlap,
        )
        provider = self._provider(data_set)

        # Generate embeddings outside the transaction — API calls must not hold a DB lock.
        pieces = splitter.split_text(entity.get_indexable_content())
        embeddings = [provider.generate_embeddings(piece) for piece in pieces]

        with transaction.atomic():
            # Lock the entity row so a concurrent sync job blocks here rather than
            # racing through the delete and producing duplicate chunk rows.
            entity.__class__.objects.select_for_update().get(pk=entity.pk)
            entity.chunks.all().delete()
            for piece, embedding in zip(pieces, embeddings):
                chunk = entity.chunks.create(content=piece)
                chunk.set_embedding(embedding)
                chunk.save()

    def _provider(self, data_set: Any) -> EmbeddingProvider:
        # Built from the DataSet itself: a lookup by id misses temporary ones, such as evaluation sandboxes.
        provider_class = self._registry.provider_class_by_name(data_set.embedding_provider)
        return provider_class(data_set.embedding_model, data_set.embedding_vector_dimensions)
