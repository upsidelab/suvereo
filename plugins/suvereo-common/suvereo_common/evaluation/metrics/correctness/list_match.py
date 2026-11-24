from pydantic import BaseModel, ConfigDict
from suvereo_common.evaluation.metrics.base_metric import BaseMetric
from suvereo_common.evaluation.metrics.matching import DottedPath, ListScorer, MatchMode
from suvereo_common.evaluation.metrics.metric_context import MetricContext
from suvereo_common.evaluation.metrics.metric_result import MetricResult


class ListMatchParams(BaseModel):
    """Settings for the list match metric."""

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
        """Compare the result's list items with the expected ones."""
        expected = DottedPath(f"output.{self.params.expected_path or self.params.path}").value_in(context.case.expected)
        if not isinstance(expected, list):
            return MetricResult(value=None, details={"reason": "the case expects no list at this path"})
        actual = DottedPath(self.params.path).value_in(context.trace.output or {})
        actual = actual if isinstance(actual, (list, tuple)) else []
        score = ListScorer(self.params.key, self.params.fields, self.params.coerce).score(list(actual), expected)
        return MetricResult(
            value=score.f1,
            components={"precision": score.precision, "recall": score.recall},
            details=score.model_dump(exclude={"matched"}),
        )
