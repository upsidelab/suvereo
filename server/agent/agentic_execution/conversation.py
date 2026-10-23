from enthusiast_common.agentic_execution import BaseAgenticExecutionDefinition, ExecutionConversationInterface
from enthusiast_common.agentic_execution.memory import ToolScratchpad

from agent.conversation.manager import ConversationManager
from agent.core.agents.config_overrides import AgentConfigOverrides
from agent.models.conversation import Conversation


class ExecutionConversation(ExecutionConversationInterface):
    """The conversation an execution drives, building its agent with the definition's settings and the given overrides.

    The given overrides win over what the definition declares.
    """

    def __init__(
        self,
        conversation: Conversation,
        definition: type[BaseAgenticExecutionDefinition],
        overrides: AgentConfigOverrides | None = None,
    ) -> None:
        self._conversation = conversation
        self._overrides = (overrides or AgentConfigOverrides()).with_fallback(
            AgentConfigOverrides(system_prompt=definition.SYSTEM_PROMPT, extra_tools=definition.EXTRA_TOOLS or None)
        )
        self._tool_scratchpad = ToolScratchpad()

    def ask(self, message: str) -> str:
        """Send a user message and return the agent's reply."""
        return ConversationManager().get_answer(
            self._conversation,
            message,
            streaming=False,
            tool_scratchpad=self._tool_scratchpad,
            overrides=self._overrides,
        )

    @property
    def tool_scratchpad(self) -> ToolScratchpad:
        """The shared memory that tools write to and validators read from."""
        return self._tool_scratchpad
