from typing import Optional

from langchain_core.chat_history import BaseChatMessageHistory

from ..agentic_execution import ToolScratchpad
from ..memory import BaseMemoryCompactor
from ..structures import RepositoriesInstances
from .base import BaseInjector


class Injector(BaseInjector):
    """Default injector carrying repositories, chat history, and memory for agent tools."""

    def __init__(
        self,
        repositories: RepositoriesInstances,
        chat_history: BaseChatMessageHistory,
        tool_scratchpad: Optional[ToolScratchpad] = None,
        memory_compactor: Optional[BaseMemoryCompactor] = None,
    ):
        super().__init__(repositories)
        self._chat_history = chat_history
        self._memory_compactor = memory_compactor
        self._tool_scratchpad = tool_scratchpad or ToolScratchpad()

    @property
    def chat_history(self) -> BaseChatMessageHistory:
        return self._chat_history

    @property
    def memory_compactor(self) -> Optional[BaseMemoryCompactor]:
        return self._memory_compactor

    @property
    def tool_scratchpad(self) -> ToolScratchpad:
        return self._tool_scratchpad
