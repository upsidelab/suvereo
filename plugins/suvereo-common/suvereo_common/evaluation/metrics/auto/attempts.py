from ...suite import SuiteKind
from ..base_metric import BaseMetric
from ..metric_context import MetricContext
from ..metric_result import MetricResult


class Attempts(BaseMetric):
    """How many attempts the validator loop took."""

    NAME = "attempts"
    VALUE_TYPE = "number"
    KINDS = (SuiteKind.EXECUTION,)

    def measure(self, context: MetricContext) -> MetricResult:
        return MetricResult(value=float(len(context.trace.attempts)))
