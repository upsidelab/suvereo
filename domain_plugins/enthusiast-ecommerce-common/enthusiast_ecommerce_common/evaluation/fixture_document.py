from pydantic import BaseModel, ConfigDict

from ..structures import DocumentDetails


class FixtureDocument(BaseModel):
    """A document in a fixture set, synced like one fetched from a real document source."""

    model_config = ConfigDict(extra="ignore")

    url: str
    title: str
    content: str

    def details(self) -> DocumentDetails:
        return DocumentDetails(url=self.url, title=self.title, content=self.content)
