from typing import Literal

from pydantic import BaseModel


class ChatMessage(BaseModel):
    """One message of a conversation sent to a model: the other side's (user) or the model's own (assistant)."""

    role: Literal["user", "assistant"]
    text: str
