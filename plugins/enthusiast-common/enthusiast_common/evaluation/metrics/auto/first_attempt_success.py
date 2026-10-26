from ...suite import SuiteKind
from ..base_metric import BaseMetric
from ..metric_context import MetricContext
from ..metric_result import MetricResult
from .run_outcome import RunOutcome


class FirstAttemptSuccess(BaseMetric):
    """Whether the run did what its case asked without the validator sending the agent back."""

    NAME = "first_attempt_success"
    VALUE_TYPE = "bool"
    KINDS = (SuiteKind.EXECUTION,)

    def measure(self, context: MetricContext) -> MetricResult:
        return MetricResult(value=RunOutcome.matches_expected_outcome(context) and len(context.trace.attempts) <= 1)
