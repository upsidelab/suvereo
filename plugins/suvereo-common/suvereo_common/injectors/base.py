from abc import ABC, abstractmethod

from langchain_core.chat_history import BaseChatMessageHistory
from suvereo_common.agentic_execution import ToolScratchpad
from suvereo_common.memory import BaseMemoryCompactor
from suvereo_common.structures import RepositoriesInstances


class BaseInjector(ABC):
    def __init__(self, repositories: RepositoriesInstances):
        self.repositories = repositories

    @property
    @abstractmethod
    def chat_history(self) -> BaseChatMessageHistory:
        pass

    @property
    @abstractmethod
    def memory_compactor(self) -> BaseMemoryCompactor | None:
        pass

    @property
    @abstractmethod
    def tool_scratchpad(self) -> ToolScratchpad:
        pass
