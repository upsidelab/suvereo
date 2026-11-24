from suvereo_common.evaluation.metrics.base_metric import BaseMetric
from suvereo_common.evaluation.metrics.metric_context import MetricContext
from suvereo_common.evaluation.metrics.metric_result import MetricResult
from suvereo_common.evaluation.suite import SuiteKind


class Attempts(BaseMetric):
    """How many attempts the validator loop took."""

    NAME = "attempts"
    VALUE_TYPE = "number"
    KINDS = (SuiteKind.EXECUTION,)

    def measure(self, context: MetricContext) -> MetricResult:
        return MetricResult(value=float(len(context.trace.attempts)))
