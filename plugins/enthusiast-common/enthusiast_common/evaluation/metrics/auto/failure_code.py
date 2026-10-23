from ..base_metric import BaseMetric
from ..metric_context import MetricContext
from ..metric_result import MetricResult

RUNTIME_ERROR = "RUNTIME_ERROR"


class FailureCode(BaseMetric):
    """The run's failure code, RUNTIME_ERROR when it raised, or none when it succeeded."""

    NAME = "failure_code"
    VALUE_TYPE = "label"
    KINDS = ("execution",)

    def measure(self, context: MetricContext) -> MetricResult:
        if context.trace.error is not None:
            return MetricResult(value=RUNTIME_ERROR, details={"error": context.trace.error})
        result = context.trace.execution_result
        return MetricResult(value=None if result is None or result.success else result.failure_code)
