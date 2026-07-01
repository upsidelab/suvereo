from abc import ABC, abstractmethod
from typing import Optional

from enthusiast_common.agentic_execution import ToolScratchpad
from enthusiast_common.memory import BaseMemoryCompactor
from enthusiast_common.structures import RepositoriesInstances
from langchain_core.chat_history import BaseChatMessageHistory


class BaseInjector(ABC):
    def __init__(self, repositories: RepositoriesInstances):
        self.repositories = repositories

    @property
    @abstractmethod
    def chat_history(self) -> BaseChatMessageHistory:
        pass

    @property
    @abstractmethod
    def memory_compactor(self) -> Optional[BaseMemoryCompactor]:
        pass

    @property
    @abstractmethod
    def tool_scratchpad(self) -> ToolScratchpad:
        pass
