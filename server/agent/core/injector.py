from typing import Optional

from enthusiast_common.agentic_execution.memory import ToolScratchpad
from enthusiast_common.injectors import BaseInjector
from enthusiast_common.structures import RepositoriesInstances
from langchain_core.chat_history import BaseChatMessageHistory

from agent.core.memory import LLMMemoryCompactor, PersistentChatHistory


class Injector(BaseInjector):
    def __init__(
        self,
        repositories: RepositoriesInstances,
        chat_history: PersistentChatHistory,
        tool_scratchpad: Optional[ToolScratchpad] = None,
        memory_compactor: Optional[LLMMemoryCompactor] = None,
    ):
        super().__init__(repositories)
        self._chat_history = chat_history
        self._memory_compactor = memory_compactor
        self._tool_scratchpad = tool_scratchpad or ToolScratchpad()

    @property
    def chat_history(self) -> BaseChatMessageHistory:
        return self._chat_history

    @property
    def memory_compactor(self) -> Optional[LLMMemoryCompactor]:
        return self._memory_compactor

    @property
    def tool_scratchpad(self) -> ToolScratchpad:
        return self._tool_scratchpad
