from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.language_models import BaseLanguageModel
from suvereo_common.repositories import BaseConversationRepository


class BaseMemoryCompactor(ABC):
    """
    Interface for keeping a long conversation within the conversation history token limit.

    The conversation is split into a summary of its older part and a window of the messages that
    follow it, which are sent verbatim. Implementations persist the summary and the boundary
    between the two, and move the boundary when the window outgrows the token limit.
    The chat history returns only the window, so the agent sends the summary followed by the
    chat history messages, and the two never overlap.

    The builder creates a compactor with the keyword arguments of ``__init__``. ``token_limit`` is the
    agent's ``conversation_history_token_limit``, and ``llm`` is the model to summarize with.
    """

    def __init__(
        self,
        conversation_repo: BaseConversationRepository,
        conversation_id: Any,
        llm: BaseLanguageModel,
        chat_history: BaseChatMessageHistory,
        token_limit: int,
    ):
        self._conversation_repo = conversation_repo
        self._conversation_id = conversation_id
        self._llm = llm
        self._chat_history = chat_history
        self._token_limit = token_limit

    @abstractmethod
    def get_summary(self) -> Optional[str]:
        """Return the current persisted summary, or None if not yet generated."""
        pass

    @abstractmethod
    def compact_if_needed(self) -> None:
        """
        Summarize the older part of the window if the window has outgrown the token limit.

        Should be called after new messages have been added to history.
        """
        pass
