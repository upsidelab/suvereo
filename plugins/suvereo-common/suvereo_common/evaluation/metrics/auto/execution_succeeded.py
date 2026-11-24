from suvereo_common.evaluation.metrics.auto.run_outcome import RunOutcome
from suvereo_common.evaluation.metrics.base_metric import BaseMetric
from suvereo_common.evaluation.metrics.metric_context import MetricContext
from suvereo_common.evaluation.metrics.metric_result import MetricResult
from suvereo_common.evaluation.suite import SuiteKind


class ExecutionSucceeded(BaseMetric):
    """Whether the run succeeded; for a case with expected.failure_code, whether it failed with that code."""

    NAME = "execution_succeeded"
    VALUE_TYPE = "bool"
    KINDS = (SuiteKind.EXECUTION,)

    def measure(self, context: MetricContext) -> MetricResult:
        """Check whether the execution succeeded."""
        return MetricResult(value=RunOutcome.matches_expected_outcome(context))
