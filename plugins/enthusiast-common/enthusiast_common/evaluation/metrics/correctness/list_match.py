from pydantic import BaseModel, ConfigDict

from ..base_metric import BaseMetric
from ..matching import DottedPath, ListScorer, MatchMode
from ..metric_context import MetricContext
from ..metric_result import MetricResult
from .expected_values import ExpectedValues


class ListMatchParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    expected_path: str | None = None
    key: str | int | None = None
    fields: dict[str | int, MatchMode] = {}
    coerce: bool = False


class ListMatch(BaseMetric):
    """F1 of an output list against the expected one, pairing items by key and checking their fields."""

    NAME = "list_match"
    VALUE_TYPE = "number"
    PARAMS = ListMatchParams

    def measure(self, context: MetricContext) -> MetricResult:
        expected = ExpectedValues.output(context.case.expected, self.params.expected_path or self.params.path)
        if not isinstance(expected, list):
            return MetricResult(value=None, details={"reason": "the case expects no list at this path"})
        actual = DottedPath(self.params.path).get(context.trace.output or {})
        actual = actual if isinstance(actual, (list, tuple)) else []
        score = ListScorer(self.params.key, self.params.fields, self.params.coerce).score(list(actual), expected)
        return MetricResult(
            value=score.f1,
            components={"precision": score.precision, "recall": score.recall},
            details=score.model_dump(exclude={"matched"}),
        )
