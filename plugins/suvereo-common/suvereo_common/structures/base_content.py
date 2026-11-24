from pydantic import BaseModel


class BaseContent(BaseModel):
    """Content passed to a language model alongside the text."""

    type: str
