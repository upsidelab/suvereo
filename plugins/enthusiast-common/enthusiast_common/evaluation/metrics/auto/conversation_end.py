from ...trace import ConversationEnding
from ..base_metric import BaseMetric
from ..metric_context import MetricContext
from ..metric_result import MetricResult


class ConversationEnd(BaseMetric):
    """How the conversation ended: done, gave_up, max_turns, or error when a turn or the run raised."""

    NAME = "conversation_end"
    VALUE_TYPE = "label"
    KINDS = ("conversation",)

    def measure(self, context: MetricContext) -> MetricResult:
        trace = context.trace
        if trace.error is not None:
            return MetricResult(value=ConversationEnding.ERROR, details={"error": trace.error})
        return MetricResult(value=trace.ended_by)
