from enthusiast_common.agentic_execution import AttemptObserver, ExecutionConversationInterface, ExecutionResult

from agent.agentic_execution.registry import AgenticExecutionDefinitionRegistry


class AgenticExecutionRunner:
    """Runs an execution definition against a conversation, independent of any task or stored execution."""

    def run(
        self,
        execution_key: str,
        input_data: dict,
        conversation: ExecutionConversationInterface,
        attempt_observer: AttemptObserver | None = None,
    ) -> ExecutionResult:
        """Validate the input against the definition's INPUT_TYPE and run it through its validator retry loop."""
        execution_cls = AgenticExecutionDefinitionRegistry().get_by_key(execution_key)
        return execution_cls().run(execution_cls.INPUT_TYPE(**input_data), conversation, attempt_observer)
