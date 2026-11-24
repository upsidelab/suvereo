from suvereo_common.evaluation.metrics.base_metric import BaseMetric
from suvereo_common.evaluation.metrics.metric_context import MetricContext
from suvereo_common.evaluation.metrics.metric_result import MetricResult
from suvereo_common.evaluation.suite import SuiteKind
from suvereo_common.evaluation.trace import StopReason


class ConversationEnd(BaseMetric):
    """How the conversation ended: done, gave_up, max_turns, or error when a turn or the run raised."""

    NAME = "conversation_end"
    VALUE_TYPE = "label"
    KINDS = (SuiteKind.CONVERSATION,)

    def measure(self, context: MetricContext) -> MetricResult:
        """Report how the conversation ended."""
        trace = context.trace
        if trace.error is not None:
            return MetricResult(value=StopReason.ERROR, details={"error": trace.error})
        return MetricResult(value=trace.stop_reason)
