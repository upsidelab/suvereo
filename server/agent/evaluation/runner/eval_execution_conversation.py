from suvereo_common.agentic_execution import BaseAgenticExecutionDefinition
from suvereo_common.agentic_execution.validators import ValidatorResponse
from suvereo_common.evaluation.trace import Attempt, TraceRecorder

from agent.agentic_execution.conversation import ExecutionConversation
from agent.core.agents.config_overrides import AgentConfigOverrides
from agent.models import Conversation


class EvalExecutionConversation(ExecutionConversation):
    """An execution conversation that records each validated attempt, and what tools left on the scratchpad, into a trace."""

    def __init__(
        self,
        conversation: Conversation,
        definition: type[BaseAgenticExecutionDefinition],
        overrides: AgentConfigOverrides,
        recorder: TraceRecorder,
    ):
        super().__init__(conversation, definition, overrides)
        self._recorder = recorder

    @property
    def conversation(self) -> Conversation:
        return self._conversation

    def record_attempt(self, number: int, response: str, failed: ValidatorResponse | None) -> None:
        """An AttemptObserver: failed is the failing validator's verdict, or None when the attempt passed."""
        self._recorder.record_attempt(
            Attempt(
                number=number,
                response=response,
                passed=failed is None,
                validator_feedback=failed.feedback if failed else None,
                failure_code=failed.failure_code if failed else None,
            )
        )

    def copy_scratchpad_to_trace(self) -> None:
        """Copy the last attempt's scratchpad into the trace."""
        self._recorder.trace.scratchpad = self.tool_scratchpad.entries()
