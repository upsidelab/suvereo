from django.db import transaction
from langchain_text_splitters import TokenTextSplitter

from agent.core.registries.embeddings import EmbeddingProviderRegistry


def index_entity(entity) -> None:
    """Chunk an entity's indexable content, embed each chunk, and store the vectors.

    Splits ``entity.get_indexable_content()`` with the DataSet's token settings, embeds
    each chunk with the DataSet's provider, and writes the chunks to the entity's chunk
    table. Existing chunks are replaced atomically — concurrent calls for the same entity
    are serialised via a row-level lock so no duplicate chunks accumulate.

    The entity must expose:
      - ``dataset`` — FK to ``catalog.DataSet`` (LLM/embedding config lives there),
      - ``get_indexable_content() -> str`` — the text to index,
      - ``chunks`` — reverse manager to its ``BaseEmbeddingChunk`` table.
    """
    data_set = entity.dataset

    splitter = TokenTextSplitter(
        chunk_size=data_set.embedding_chunk_size,
        chunk_overlap=data_set.embedding_chunk_overlap,
    )
    provider_class = EmbeddingProviderRegistry().provider_for_dataset(data_set.id)
    provider = provider_class(data_set.embedding_model, data_set.embedding_vector_dimensions)

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
