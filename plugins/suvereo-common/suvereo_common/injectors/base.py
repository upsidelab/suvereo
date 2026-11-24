from abc import ABC, abstractmethod

from langchain_core.chat_history import BaseChatMessageHistory
from suvereo_common.agentic_execution import ToolScratchpad
from suvereo_common.memory import BaseMemoryCompactor
from suvereo_common.structures import RepositoriesInstances


class BaseInjector(ABC):
    """Gives agents and tools access to data and conversation memory."""

    def __init__(self, repositories: RepositoriesInstances):
        self.repositories = repositories

    @property
    @abstractmethod
    def chat_history(self) -> BaseChatMessageHistory:
        """The conversation's chat history."""

    @property
    @abstractmethod
    def memory_compactor(self) -> BaseMemoryCompactor | None:
        """The memory compactor, or None when compaction is off."""

    @property
    @abstractmethod
    def tool_scratchpad(self) -> ToolScratchpad:
        """The scratchpad tools share during an agentic execution."""
