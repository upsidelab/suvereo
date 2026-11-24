
from langchain_core.chat_history import BaseChatMessageHistory
from suvereo_common.agentic_execution import ToolScratchpad
from suvereo_common.injectors.base import BaseInjector
from suvereo_common.memory import BaseMemoryCompactor
from suvereo_common.structures import RepositoriesInstances


class Injector(BaseInjector):
    """Default injector carrying repositories, chat history, and memory for agent tools."""

    def __init__(
        self,
        repositories: RepositoriesInstances,
        chat_history: BaseChatMessageHistory,
        tool_scratchpad: ToolScratchpad | None = None,
        memory_compactor: BaseMemoryCompactor | None = None,
    ):
        super().__init__(repositories)
        self._chat_history = chat_history
        self._memory_compactor = memory_compactor
        self._tool_scratchpad = tool_scratchpad or ToolScratchpad()

    @property
    def chat_history(self) -> BaseChatMessageHistory:
        """The conversation's chat history."""
        return self._chat_history

    @property
    def memory_compactor(self) -> BaseMemoryCompactor | None:
        """The memory compactor, or None when compaction is off."""
        return self._memory_compactor

    @property
    def tool_scratchpad(self) -> ToolScratchpad:
        """The scratchpad tools share during an agentic execution."""
        return self._tool_scratchpad
