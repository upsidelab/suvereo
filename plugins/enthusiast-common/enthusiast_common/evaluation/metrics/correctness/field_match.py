from pydantic import BaseModel, ConfigDict

from ..base_metric import BaseMetric
from ..matching import MISSING, DottedPath, MatchMode, ValueMatcher
from ..metric_context import MetricContext
from ..metric_result import MetricResult
from .expected_values import ExpectedValues


class FieldMatchParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    expected_path: str | None = None
    mode: MatchMode = "exact"
    coerce: bool = False


class FieldMatch(BaseMetric):
    """Whether one output field matches its expected value (expected.output.<expected_path>, default path)."""

    NAME = "field_match"
    VALUE_TYPE = "bool"
    PARAMS = FieldMatchParams

    def measure(self, context: MetricContext) -> MetricResult:
        expected = ExpectedValues.output(context.case.expected, self.params.expected_path or self.params.path)
        if expected is MISSING:
            return MetricResult(value=None, details={"reason": "the case expects no value at this path"})
        actual = DottedPath(self.params.path).get(context.trace.output or {})
        if actual is MISSING:
            return MetricResult(value=False, details={"expected": expected, "reason": "the output has no value here"})
        matched = ValueMatcher(self.params.mode, self.params.coerce).matches(actual, expected)
        return MetricResult(value=matched, details={} if matched else {"expected": expected, "actual": actual})
