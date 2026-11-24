from suvereo_common.evaluation.metrics.auto.run_outcome import RunOutcome
from suvereo_common.evaluation.metrics.base_metric import BaseMetric
from suvereo_common.evaluation.metrics.metric_context import MetricContext
from suvereo_common.evaluation.metrics.metric_result import MetricResult
from suvereo_common.evaluation.suite import SuiteKind


class FirstAttemptSuccess(BaseMetric):
    """Whether the run did what its case asked without the validator sending the agent back."""

    NAME = "first_attempt_success"
    VALUE_TYPE = "bool"
    KINDS = (SuiteKind.EXECUTION,)

    def measure(self, context: MetricContext) -> MetricResult:
        """Check whether the run succeeded on its first attempt."""
        return MetricResult(value=RunOutcome.matches_expected_outcome(context) and len(context.trace.attempts) <= 1)
