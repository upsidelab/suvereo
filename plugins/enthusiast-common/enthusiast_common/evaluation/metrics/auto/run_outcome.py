from ..metric_context import MetricContext

EXPECTED_FAILURE_KEY = "failure_code"


class RunOutcome:
    """Whether a run did what its case asked: succeed, or fail with the code under expected.failure_code."""

    @staticmethod
    def matches_expected_outcome(context: MetricContext) -> bool:
        result, expected_failure = context.trace.execution_result, context.case.expected.get(EXPECTED_FAILURE_KEY)
        if context.trace.error is not None or result is None:
            return False
        if expected_failure is not None:
            return not result.success and result.failure_code == expected_failure
        return result.success
