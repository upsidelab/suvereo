from suvereo_common.agentic_execution import BaseAgenticExecutionDefinition
from suvereo_common.agentic_execution.validators import ValidatorResponse
from suvereo_common.evaluation.trace import Attempt, TraceRecorder

from agent.agentic_execution.conversation import ExecutionConversation
from agent.core.agents.config_overrides import AgentConfigOverrides
from agent.models import Conversation


class EvalExecutionConversation(ExecutionConversation):
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
        self._recorder.trace.scratchpad = self.tool_scratchpad.entries()
