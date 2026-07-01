from langchain_text_splitters import TokenTextSplitter

from agent.core.registries.embeddings import EmbeddingProviderRegistry


def index_entity(entity) -> None:
    """Chunk an entity's indexable content, embed each chunk, and store the vectors.

    Splits ``entity.get_indexable_content()`` with the DataSet's token settings, embeds
    each chunk with the DataSet's provider, and writes the chunks to the entity's chunk
    table. Existing chunks are replaced.

    The entity must expose:
      - ``dataset`` — FK to ``catalog.DataSet`` (LLM/embedding config lives there),
      - ``get_indexable_content() -> str`` — the text to index,
      - ``chunks`` — reverse manager to its ``BaseEmbeddingChunk`` table.
    """
    data_set = entity.dataset
    entity.chunks.all().delete()

    splitter = TokenTextSplitter(
        chunk_size=data_set.embedding_chunk_size,
        chunk_overlap=data_set.embedding_chunk_overlap,
    )
    provider_class = EmbeddingProviderRegistry().provider_for_dataset(data_set.id)
    provider = provider_class(data_set.embedding_model, data_set.embedding_vector_dimensions)

    for piece in splitter.split_text(entity.get_indexable_content()):
        chunk = entity.chunks.create(content=piece)
        chunk.set_embedding(provider.generate_embeddings(piece))
        chunk.save()
