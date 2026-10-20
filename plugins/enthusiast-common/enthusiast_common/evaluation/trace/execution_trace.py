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
    parent_run_ids: dict[str, str] = {}

    def record_llm_call(self, call: LLMCall) -> bool:
        """Add a finished LLM call; False when its run_id is already recorded."""
        if any(c.run_id == call.run_id for c in self.llm_calls):
            return False
        self.llm_calls.append(call)
        return True

    def record_tool_call(self, call: ToolCall) -> bool:
        """Add a finished tool call; False when its run_id is already recorded."""
        if any(c.run_id == call.run_id for c in self.tool_calls):
            return False
        self.tool_calls.append(call)
        return True

    def record_run_parent(self, run_id: str, parent_run_id: str) -> None:
        """Remember which run started another one."""
        self.parent_run_ids[run_id] = parent_run_id

    def record_mock_call(self, call: MockCall) -> None:
        """Add a call a mock received."""
        self.mock_calls.append(call)

    def record_attempt(self, attempt: Attempt) -> None:
        """Add one pass of the execution's validator loop."""
        self.attempts.append(attempt)

    def tool_calls_named(self, name: str) -> list[ToolCall]:
        """The agent's calls to one tool, in order."""
        return [c for c in self.tool_calls if c.name == name]

    def mock_calls_to(self, method: str) -> list[MockCall]:
        """The calls mocks received to one method, in order."""
        return [c for c in self.mock_calls if c.method == method]

    def llm_calls_within(self, tool_call: ToolCall) -> list[LLMCall]:
        """The LLM calls made anywhere inside a tool call, also through chains the tool ran."""
        return [c for c in self.llm_calls if tool_call.run_id in self._ancestor_runs(c.parent_run_id)]

    def _ancestor_runs(self, run_id: str | None) -> list[str]:
        """A run and every run above it, following parent_run_ids."""
        ancestors: list[str] = []
        while run_id is not None and run_id not in ancestors:
            ancestors.append(run_id)
            run_id = self.parent_run_ids.get(run_id)
        return ancestors

    def had_retry(self) -> bool:
        """Whether the validator loop sent the agent back for another attempt."""
        return len(self.attempts) > 1

    def had_tool_error(self) -> bool:
        """Whether any tool call raised."""
        return any(c.error for c in self.tool_calls)

    def had_validator_failure(self, failure_code: str | None = None) -> bool:
        """Whether any attempt failed validation, optionally with a given failure code."""
        return any(not a.passed and (failure_code is None or a.failure_code == failure_code) for a in self.attempts)

    @property
    def input_tokens(self) -> int:
        """Input tokens over every LLM call, nested ones included."""
        return sum(c.input_tokens for c in self.llm_calls)

    @property
    def output_tokens(self) -> int:
        """Output tokens over every LLM call, nested ones included."""
        return sum(c.output_tokens for c in self.llm_calls)
