from threading import Lock

from .attempt import Attempt
from .execution_trace import ExecutionTrace
from .llm_call import LLMCall
from .mock_call import MockCall
from .tool_call import ToolCall


class TraceRecorder:
    """Records into one run's trace from any thread; parallel tool calls report from several at once."""

    def __init__(self, trace: ExecutionTrace | None = None):
        self.trace = trace if trace is not None else ExecutionTrace()
        self._lock = Lock()

    def record_llm_call(self, call: LLMCall) -> bool:
        """Record a finished LLM call.

        Args:
            call: The call; ignored if its ``run_id`` is already recorded.

        Returns:
            False when the call was already recorded by another handler.
        """
        with self._lock:
            return self.trace.record_llm_call(call)

    def record_tool_call(self, call: ToolCall) -> bool:
        """Record a finished tool call.

        Args:
            call: The call; ignored if its ``run_id`` is already recorded.

        Returns:
            False when the call was already recorded by another handler.
        """
        with self._lock:
            return self.trace.record_tool_call(call)

    def record_mock_call(self, call: MockCall) -> None:
        """Record a call a mock received.

        Args:
            call: The call; mocks record each call once, so nothing is deduplicated.
        """
        with self._lock:
            self.trace.record_mock_call(call)

    def record_attempt(self, attempt: Attempt) -> None:
        """Record one pass of the execution's validator loop.

        Args:
            attempt: The attempt, numbered from 1.
        """
        with self._lock:
            self.trace.record_attempt(attempt)
