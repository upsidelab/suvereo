from suvereo_common.agentic_execution import BaseAgenticExecutionDefinition, ExecutionConversationInterface
from suvereo_common.agentic_execution.memory import ToolScratchpad

from agent.conversation.manager import ConversationManager
from agent.core.agents.config_overrides import AgentConfigOverrides
from agent.models.conversation import Conversation


class ExecutionConversation(ExecutionConversationInterface):
    def __init__(
        self,
        conversation: Conversation,
        definition: type[BaseAgenticExecutionDefinition],
        overrides: AgentConfigOverrides | None = None,
    ) -> None:
        self._conversation = conversation
        self._overrides = (overrides or AgentConfigOverrides()).with_fallback(
            AgentConfigOverrides(system_prompt=definition.SYSTEM_PROMPT, tools=definition.TOOLS)
        )
        self._tool_scratchpad = ToolScratchpad()

    def ask(self, message: str) -> str:
        return ConversationManager().get_answer(
            self._conversation,
            message,
            streaming=False,
            tool_scratchpad=self._tool_scratchpad,
            overrides=self._overrides,
        )

    @property
    def tool_scratchpad(self) -> ToolScratchpad:
        return self._tool_scratchpad
