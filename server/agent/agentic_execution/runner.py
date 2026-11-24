from suvereo_common.agentic_execution import AttemptObserver, ExecutionConversationInterface, ExecutionResult

from agent.agentic_execution.registry import AgenticExecutionDefinitionRegistry


class AgenticExecutionRunner:
    def run(
        self,
        execution_key: str,
        input_data: dict,
        conversation: ExecutionConversationInterface,
        attempt_observer: AttemptObserver | None = None,
    ) -> ExecutionResult:
        execution_cls = AgenticExecutionDefinitionRegistry().get_by_key(execution_key)
        return execution_cls().run(execution_cls.INPUT_TYPE(**input_data), conversation, attempt_observer)
