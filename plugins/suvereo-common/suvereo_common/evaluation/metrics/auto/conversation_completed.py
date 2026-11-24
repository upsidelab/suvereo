from suvereo_common.evaluation.metrics.base_metric import BaseMetric
from suvereo_common.evaluation.metrics.metric_context import MetricContext
from suvereo_common.evaluation.metrics.metric_result import MetricResult
from suvereo_common.evaluation.suite import SuiteKind
from suvereo_common.evaluation.trace import StopReason


class ConversationCompleted(BaseMetric):
    """Whether the user finished the conversation: at least one turn, every turn answered, and the user said done."""

    NAME = "conversation_completed"
    VALUE_TYPE = "bool"
    KINDS = (SuiteKind.CONVERSATION,)

    def measure(self, context: MetricContext) -> MetricResult:
        trace = context.trace
        answered = bool(trace.turns) and all(turn.answer is not None for turn in trace.turns)
        return MetricResult(value=answered and trace.error is None and trace.stop_reason == StopReason.DONE)
