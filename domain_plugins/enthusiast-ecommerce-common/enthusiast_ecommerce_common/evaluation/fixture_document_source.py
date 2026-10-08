from ..interfaces import DocumentSourcePlugin
from ..structures import DocumentDetails


class FixtureDocumentSource(DocumentSourcePlugin):
    """A document source serving fixture documents, so syncing fills a sandbox DataSet with them."""

    TYPE = "fixture_document_source"
    NAME = "Fixture documents"

    def __init__(self, documents: list[DocumentDetails]):
        self._documents = documents

    def fetch(self) -> list[DocumentDetails]:
        return list(self._documents)
