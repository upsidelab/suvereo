

class DocumentRetriever:
    """Retrieves document chunks from the vertical's DocumentChunk table using vector similarity."""

    def __init__(self, data_set_id: int, max_results: int = 12):
        self.data_set_id = data_set_id
        self.max_results = max_results

    # TODO: Mirror the document retriever functionality from Enthusiast