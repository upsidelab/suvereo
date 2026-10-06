from typing import Any

from pydantic import BaseModel

from ...agentic_execution.result import ExecutionResult
from .attempt import Attempt
from .llm_call import LLMCall
from .mock_call import MockCall
from .tool_call import ToolCall


class ExecutionTrace(BaseModel):
    """Everything that happened in one run, kept once per run_id; record through a TraceRecorder while it runs."""

    llm_calls: list[LLMCall] = []
    tool_calls: list[ToolCall] = []
    attempts: list[Attempt] = []
    mock_calls: list[MockCall] = []
    scratchpad: dict[str, Any] = {}
    output: dict[str, Any] | None = None
    execution_result: ExecutionResult | None = None
    error: str | None = None

    def record_llm_call(self, call: LLMCall) -> bool:
        """Record a finished LLM call.

        Args:
            call: The call; ignored if its ``run_id`` is already recorded.

        Returns:
            False when the call was already recorded by another handler.
        """
        if any(c.run_id == call.run_id for c in self.llm_calls):
            return False
        self.llm_calls.append(call)
        return True

    def record_tool_call(self, call: ToolCall) -> bool:
        """Record a finished tool call.

        Args:
            call: The call; ignored if its ``run_id`` is already recorded.

        Returns:
            False when the call was already recorded by another handler.
        """
        if any(c.run_id == call.run_id for c in self.tool_calls):
            return False
        self.tool_calls.append(call)
        return True

    def record_mock_call(self, call: MockCall) -> None:
        """Record a call a mock received.

        Args:
            call: The call; mocks record each call once, so nothing is deduplicated.
        """
        self.mock_calls.append(call)

    def record_attempt(self, attempt: Attempt) -> None:
        """Record one pass of the execution's validator loop.

        Args:
            attempt: The attempt, numbered from 1.
        """
        self.attempts.append(attempt)

    def tool_calls_named(self, name: str) -> list[ToolCall]:
        """The agent's calls to one tool.

        Args:
            name: The tool's name.

        Returns:
            The calls in the order they finished.
        """
        return [c for c in self.tool_calls if c.name == name]

    def mock_calls_to(self, method: str) -> list[MockCall]:
        """The calls mocks received to one method.

        Args:
            method: The interface method's name.

        Returns:
            The calls in the order they were made.
        """
        return [c for c in self.mock_calls if c.method == method]

    def llm_calls_within(self, tool_call: ToolCall) -> list[LLMCall]:
        """The LLM calls made directly inside a tool call.

        Args:
            tool_call: The tool call to look inside.

        Returns:
            The calls whose parent is that tool call.
        """
        return [c for c in self.llm_calls if c.parent_run_id == tool_call.run_id]

    def had_retry(self) -> bool:
        """Whether the validator loop sent the agent back for another attempt.

        Returns:
            True when more than one attempt was recorded.
        """
        return len(self.attempts) > 1

    def had_tool_error(self) -> bool:
        """Whether any tool call raised.

        Returns:
            True when a recorded tool call has an error.
        """
        return any(c.error for c in self.tool_calls)

    def had_validator_failure(self, failure_code: str | None = None) -> bool:
        """Whether any attempt failed validation.

        Args:
            failure_code: Only count failures with this code; any code when None.

        Returns:
            True when a matching failed attempt was recorded.
        """
        return any(not a.passed and (failure_code is None or a.failure_code == failure_code) for a in self.attempts)

    @property
    def input_tokens(self) -> int:
        """Input tokens over every LLM call, nested ones included."""
        return sum(c.input_tokens for c in self.llm_calls)

    @property
    def output_tokens(self) -> int:
        """Output tokens over every LLM call, nested ones included."""
        return sum(c.output_tokens for c in self.llm_calls)
