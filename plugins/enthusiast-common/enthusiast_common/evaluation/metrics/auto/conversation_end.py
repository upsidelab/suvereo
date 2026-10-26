from ...suite import SuiteKind
from ...trace import StopReason
from ..base_metric import BaseMetric
from ..metric_context import MetricContext
from ..metric_result import MetricResult


class ConversationEnd(BaseMetric):
    """How the conversation ended: done, gave_up, max_turns, or error when a turn or the run raised."""

    NAME = "conversation_end"
    VALUE_TYPE = "label"
    KINDS = (SuiteKind.CONVERSATION,)

    def measure(self, context: MetricContext) -> MetricResult:
        trace = context.trace
        if trace.error is not None:
            return MetricResult(value=StopReason.ERROR, details={"error": trace.error})
        return MetricResult(value=trace.stop_reason)
