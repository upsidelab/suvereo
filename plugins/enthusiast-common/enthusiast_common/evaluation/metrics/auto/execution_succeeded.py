from ..base_metric import BaseMetric
from ..metric_context import MetricContext
from ..metric_result import MetricResult
from .run_outcome import RunOutcome


class ExecutionSucceeded(BaseMetric):
    """Whether the run succeeded; for a case with expected.failure_code, whether it failed with that code."""

    NAME = "execution_succeeded"
    VALUE_TYPE = "bool"
    KINDS = ("execution",)

    def measure(self, context: MetricContext) -> MetricResult:
        return MetricResult(value=RunOutcome.matches_expected_outcome(context))
