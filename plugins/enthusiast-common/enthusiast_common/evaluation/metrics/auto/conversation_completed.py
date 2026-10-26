from ...suite import SuiteKind
from ...trace import StopReason
from ..base_metric import BaseMetric
from ..metric_context import MetricContext
from ..metric_result import MetricResult


class ConversationCompleted(BaseMetric):
    """Whether the user finished the conversation: at least one turn, every turn answered, and the user said done."""

    NAME = "conversation_completed"
    VALUE_TYPE = "bool"
    KINDS = (SuiteKind.CONVERSATION,)

    def measure(self, context: MetricContext) -> MetricResult:
        trace = context.trace
        answered = bool(trace.turns) and all(turn.answer is not None for turn in trace.turns)
        return MetricResult(value=answered and trace.error is None and trace.stop_reason == StopReason.DONE)
