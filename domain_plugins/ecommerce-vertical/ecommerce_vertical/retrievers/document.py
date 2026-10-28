from suvereo_common.retrievers import BaseVectorStoreRetriever

from ecommerce_vertical.models import DocumentChunk


class DocumentRetriever(BaseVectorStoreRetriever[DocumentChunk]):
    """Retrieves document chunks from the vertical's DocumentChunk table using vector similarity."""

    chunk_model = DocumentChunk
    dataset_filter = "document__dataset_id"
