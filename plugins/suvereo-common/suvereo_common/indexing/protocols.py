from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IndexableEntity(Protocol):
    """Structural contract an entity must satisfy to be indexed by ``BaseEntityIndexer``.

    Domain models satisfy this by shape alone — no inheritance required:
      - ``dataset`` — the DataSet-like object holding the embedding configuration,
      - ``get_indexable_content()`` — the text to chunk and embed,
      - ``chunks`` — reverse manager to the entity's ``BaseEmbeddingChunk`` table
        (a foreign key on the chunk model declared with ``related_name="chunks"``),
      - ``pk`` — used to lock the row during re-indexing.
    """

    pk: Any
    dataset: Any
    chunks: Any

    def get_indexable_content(self) -> str:
        """Return the text content to be chunked and embedded."""
        ...
