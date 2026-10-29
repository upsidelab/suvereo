from abc import ABC, abstractmethod

from .chat_message import ChatMessage
from .suite import ModelTarget


class BaseModelClient(ABC):
    """A model the evaluation asks besides the agent, e.g. a judge or a simulated user; the host implements it and
    tracks its cost."""

    @abstractmethod
    def chat(self, messages: list[ChatMessage], system: str | None = None, model: ModelTarget | None = None) -> str:
        """Send a conversation, after the system prompt when given, and return the model's next reply; model
        overrides the client's own model for this call."""

    def complete(self, prompt: str, model: ModelTarget | None = None) -> str:
        """Ask one question and return the text reply; model overrides the client's own model for this call."""
        return self.chat([ChatMessage(role="user", text=prompt)], model=model)
