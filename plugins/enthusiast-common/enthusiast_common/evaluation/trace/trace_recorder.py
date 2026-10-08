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
        """Add a finished LLM call; False when its run_id is already recorded."""
        with self._lock:
            return self.trace.record_llm_call(call)

    def record_tool_call(self, call: ToolCall) -> bool:
        """Add a finished tool call; False when its run_id is already recorded."""
        with self._lock:
            return self.trace.record_tool_call(call)

    def record_mock_call(self, call: MockCall) -> None:
        """Add a call a mock received."""
        with self._lock:
            self.trace.record_mock_call(call)

    def record_attempt(self, attempt: Attempt) -> None:
        """Add one pass of the execution's validator loop."""
        with self._lock:
            self.trace.record_attempt(attempt)
