from enthusiast_common.evaluation.metrics import BaseMetric, MetricResult
from pydantic import BaseModel


class ThresholdParams(BaseModel):
    threshold: float = 0.5


class AttemptsAtMost(BaseMetric):
    """Whether the run needed at most a number of attempts."""

    NAME = "attempts_at_most"
    VALUE_TYPE = "bool"
    PARAMS = ThresholdParams

    def measure(self, context):
        return MetricResult(value=len(context.trace.attempts) <= self.params.threshold)
