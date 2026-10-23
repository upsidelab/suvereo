from ...suite import SuiteKind
from ..base_metric import BaseMetric
from .attempts import Attempts
from .conversation_completed import ConversationCompleted
from .cost_usd import CostUsd
from .duration_seconds import DurationSeconds
from .execution_succeeded import ExecutionSucceeded
from .failure_code import FailureCode
from .first_attempt_success import FirstAttemptSuccess
from .input_tokens import InputTokens
from .llm_calls import LLMCalls
from .output_tokens import OutputTokens
from .tool_calls import ToolCalls
from .turns import Turns

#: Measured with no configuration, each on every run of the suite kinds it declares.
AUTO_METRICS = [
    ExecutionSucceeded,
    FailureCode,
    Attempts,
    FirstAttemptSuccess,
    ConversationCompleted,
    Turns,
    DurationSeconds,
    CostUsd,
    InputTokens,
    OutputTokens,
    LLMCalls,
    ToolCalls,
]


def auto_metrics_for(kind: SuiteKind) -> list[type[BaseMetric]]:
    """The auto metrics measured on every run of a suite of this kind."""
    return [metric for metric in AUTO_METRICS if kind in metric.KINDS]


__all__ = [
    "AUTO_METRICS",
    "Attempts",
    "ConversationCompleted",
    "CostUsd",
    "DurationSeconds",
    "ExecutionSucceeded",
    "FailureCode",
    "FirstAttemptSuccess",
    "InputTokens",
    "LLMCalls",
    "OutputTokens",
    "ToolCalls",
    "Turns",
    "auto_metrics_for",
]
