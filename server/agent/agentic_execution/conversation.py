from typing import Optional

from enthusiast_common.agentic_execution import ExecutionConversationInterface
from enthusiast_common.agentic_execution.memory import ToolScratchpad
from enthusiast_common.agents import ConfigType

from agent.conversation.manager import ConversationManager
from agent.core.agents.config_overrides import AgentConfigOverrides
from agent.models.conversation import Conversation


class ExecutionConversation(ExecutionConversationInterface):
    """The conversation handle an execution drives, backed by a stored ``Conversation``.

    Args:
        conversation: The conversation every ``ask()`` appends to.
        overrides: Applied to the agent built for each ``ask()``; None builds it as configured.
    """

    def __init__(self, conversation: Conversation, overrides: Optional[AgentConfigOverrides] = None) -> None:
        self._conversation = conversation
        self._overrides = overrides
        self._tool_scratchpad = ToolScratchpad()

    def ask(self, message: str) -> str:
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
