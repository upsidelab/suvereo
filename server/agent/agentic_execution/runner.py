from enthusiast_common.agentic_execution import ExecutionConversationInterface, ExecutionResult

from agent.agentic_execution.registry import AgenticExecutionDefinitionRegistry


class AgenticExecutionRunner:
    """Runs an execution definition against a conversation, independent of any task or stored execution."""

    def run(
        self, execution_key: str, input_data: dict, conversation: ExecutionConversationInterface
    ) -> ExecutionResult:
        """Run the execution definition registered under a key.

        Args:
            execution_key: The definition's ``EXECUTION_KEY``.
            input_data: Raw input, validated against the definition's ``INPUT_TYPE``.
            conversation: The conversation the definition drives.

        Returns:
            The definition's result, after its validator retry loop.

        Raises:
            pydantic.ValidationError: If ``input_data`` does not fit the definition's ``INPUT_TYPE``.
        """
        execution_cls = AgenticExecutionDefinitionRegistry().get_by_key(execution_key)
        return execution_cls().run(execution_cls.INPUT_TYPE(**input_data), conversation)
