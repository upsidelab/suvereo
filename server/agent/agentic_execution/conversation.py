from enthusiast_common.agentic_execution import ExecutionConversationInterface
from enthusiast_common.agentic_execution.memory import ToolScratchpad
from enthusiast_common.agents import ConfigType

from agent.conversation.manager import ConversationManager
from agent.core.agents.config_overrides import AgentConfigOverrides
from agent.models.conversation import Conversation


class ExecutionConversation(ExecutionConversationInterface):
    """The conversation an execution drives, building its agent with the given overrides."""

    def __init__(self, conversation: Conversation, overrides: AgentConfigOverrides | None = None) -> None:
        self._conversation = conversation
        self._overrides = overrides
        self._tool_scratchpad = ToolScratchpad()

    def ask(self, message: str) -> str:
        """Send a user message and return the agent's reply."""
        return ConversationManager().get_answer(
            self._conversation,
            message,
            streaming=False,
            config_type=ConfigType.AGENTIC_EXECUTION_DEFINITION,
            tool_scratchpad=self._tool_scratchpad,
            overrides=self._overrides,
        )

    @property
    def tool_scratchpad(self) -> ToolScratchpad:
        """The shared memory that tools write to and validators read from."""
        return self._tool_scratchpad
