from abc import ABC, abstractmethod
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler


class ConversationCallbackHandler(ABC, BaseCallbackHandler):
    """A callback handler that sends events to a conversation's client."""

    @abstractmethod
    def send_message(self, message_data: Any) -> None:
        """Send one event to the conversation's client."""
