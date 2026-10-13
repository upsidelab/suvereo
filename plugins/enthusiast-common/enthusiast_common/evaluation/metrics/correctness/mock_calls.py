from pydantic import BaseModel, ConfigDict

from ..base_metric import BaseMetric
from ..matching import MISSING, DottedPath, ListScore, ListScorer, MatchMode
from ..metric_context import MetricContext
from ..metric_result import MetricResult


class MockCallsParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str
    arg: str
    key: str | int | None = None
    fields: dict[str | int, MatchMode] = {}
    coerce: bool = False


class MockCalls(BaseMetric):
    """F1 of one argument across a mock method's calls against expected.mock_calls.<method>[i].<arg>; list arguments are scored per item."""

    NAME = "mock_calls"
    VALUE_TYPE = "number"
    PARAMS = MockCallsParams

    def measure(self, context: MetricContext) -> MetricResult:
        expected_calls = DottedPath(f"mock_calls.{self.params.method}").value_in(context.case.expected)
        if expected_calls is MISSING or not isinstance(expected_calls, list):
            return MetricResult(value=None, details={"reason": f"the case expects no calls to {self.params.method}"})
        if not all(isinstance(call, dict) for call in expected_calls):
            return MetricResult(
                value=None,
                details={"reason": f"each expected call to {self.params.method} must be a mapping of arguments"},
            )
        actual_calls = context.trace.mock_calls_to(self.params.method)
        scorer = ListScorer(self.params.key, self.params.fields, self.params.coerce)
        score = ListScore()
        for index in range(max(len(expected_calls), len(actual_calls))):
            wanted = expected_calls[index].get(self.params.arg) if index < len(expected_calls) else None
            got = actual_calls[index].arguments.get(self.params.arg) if index < len(actual_calls) else None
            score = score.combined_with(scorer.score(self._as_list(got), self._as_list(wanted)))
        return MetricResult(
            value=score.f1,
            components={"precision": score.precision, "recall": score.recall},
            details={
                "calls": len(actual_calls),
                "expected_calls": len(expected_calls),
                **score.model_dump(exclude={"matched"}),
            },
        )

    @staticmethod
    def _as_list(value) -> list:
        if value is None:
            return []
        return list(value) if isinstance(value, (list, tuple)) else [value]
