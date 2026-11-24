from typing import Any

from django.db import transaction
from langchain_text_splitters import TokenTextSplitter
from suvereo_common.indexing import BaseEntityIndexer, IndexableEntity
from suvereo_common.registry import BaseEmbeddingProviderRegistry, EmbeddingProvider


class EmbeddingIndexer(BaseEntityIndexer):
    def __init__(self, registry: BaseEmbeddingProviderRegistry):
        self._registry = registry

    def index(self, entity: IndexableEntity) -> None:
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
            for piece, embedding in zip(pieces, embeddings, strict=False):
                chunk = entity.chunks.create(content=piece)
                chunk.set_embedding(embedding)
                chunk.save()

    def _provider(self, data_set: Any) -> EmbeddingProvider:
        # Built from the DataSet itself: a lookup by id misses temporary ones, such as evaluation sandboxes.
        provider_class = self._registry.provider_class_by_name(data_set.embedding_provider)
        return provider_class(data_set.embedding_model, data_set.embedding_vector_dimensions)
