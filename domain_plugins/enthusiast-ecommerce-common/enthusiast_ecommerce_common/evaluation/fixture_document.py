from pydantic import BaseModel, ConfigDict

from ..structures import DocumentDetails


class FixtureDocument(BaseModel):
    """A document in a fixture set, synced like one fetched from a real document source."""

    model_config = ConfigDict(extra="ignore")

    url: str
    title: str
    content: str

    def to_document_details(self) -> DocumentDetails:
        """The document as the document source returns it."""
        return DocumentDetails(url=self.url, title=self.title, content=self.content)
