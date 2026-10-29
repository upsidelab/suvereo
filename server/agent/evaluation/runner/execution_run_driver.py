from suvereo_common.evaluation.base_model_client import BaseModelClient
from suvereo_common.evaluation.suite import AgenticExecutionEvalCase, EvalCase
from suvereo_common.evaluation.trace import TraceRecorder

from agent.agentic_execution.registry import AgenticExecutionDefinitionRegistry
from agent.agentic_execution.runner import AgenticExecutionRunner
from agent.core.agents.config_overrides import AgentConfigOverrides
from agent.models import Conversation

from .base_run_driver import BaseRunDriver
from .eval_execution_conversation import EvalExecutionConversation


class ExecutionRunDriver(BaseRunDriver):
    """Runs the case's input through an agentic execution and its validator loop, recording each attempt."""

    def __init__(self, execution_key: str):
        self.execution_key = execution_key

    def run(
        self,
        case: EvalCase,
        conversation: Conversation,
        overrides: AgentConfigOverrides,
        recorder: TraceRecorder,
        user_llm: BaseModelClient | None = None,
    ) -> None:
        if not isinstance(case, AgenticExecutionEvalCase):
            raise TypeError(f"Case '{case.id}' is not an execution case; this suite runs executions.")
        execution_conversation = EvalExecutionConversation(
            conversation, AgenticExecutionDefinitionRegistry().get_by_key(self.execution_key), overrides, recorder
        )
        try:
            result = AgenticExecutionRunner().run(
                self.execution_key, case.input, execution_conversation, execution_conversation.record_attempt
            )
            recorder.trace.execution_result = result
            recorder.trace.output = result.output if result.success else None
        finally:
            execution_conversation.copy_scratchpad_to_trace()
