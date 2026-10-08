from .attempts import Attempts
from .cost_usd import CostUsd
from .duration_seconds import DurationSeconds
from .execution_succeeded import ExecutionSucceeded
from .failure_code import FailureCode
from .first_attempt_success import FirstAttemptSuccess
from .input_tokens import InputTokens
from .llm_calls import LLMCalls
from .output_tokens import OutputTokens
from .tool_calls import ToolCalls

#: Measured on every run with no configuration.
AUTO_METRICS = [
    ExecutionSucceeded,
    FailureCode,
    Attempts,
    FirstAttemptSuccess,
    DurationSeconds,
    CostUsd,
    InputTokens,
    OutputTokens,
    LLMCalls,
    ToolCalls,
]

__all__ = [
    "AUTO_METRICS",
    "Attempts",
    "CostUsd",
    "DurationSeconds",
    "ExecutionSucceeded",
    "FailureCode",
    "FirstAttemptSuccess",
    "InputTokens",
    "LLMCalls",
    "OutputTokens",
    "ToolCalls",
]
