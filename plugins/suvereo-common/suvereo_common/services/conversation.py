from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from suvereo_common.repositories import (
    BaseConversationRepository,
    BaseMessageRepository,
    BaseUserRepository,
)

T = TypeVar("T")


class BaseConversationService(ABC, Generic[T]):
    """Creates conversations and records their messages."""

    def __init__(
        self,
        conversation_repo: BaseConversationRepository,
        message_repo: BaseMessageRepository,
        user_repo: BaseUserRepository,
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.user_repo = user_repo

    @abstractmethod
    def create_conversation(self, user_id: Any, data_set_id: Any) -> T:
        """Create a conversation for the user in the data set."""

    @abstractmethod
    def save_user_message(self, conversation_id: Any, message: str) -> Any:
        """Save a message the user sent."""

    @abstractmethod
    def get_messages(self, conversation_id: Any) -> list[Any]:
        """Return the conversation's messages."""

    @abstractmethod
    def record_error(self, conversation_id: Any) -> None:
        """Record that answering the conversation failed."""
