from typing import Any

from pydantic import BaseModel, ConfigDict

from ..base_metric import BaseMetric
from ..matching import MISSING, DottedPath, MatchMode, ValueMatcher
from ..metric_context import MetricContext
from ..metric_result import MetricResult


class JsonSubsetParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = ""
    modes: dict[str, MatchMode] = {}
    coerce: bool = False


class JsonSubset(BaseMetric):
    """The share of expected output fields the output matches; fields the case does not expect are ignored."""

    NAME = "json_subset"
    VALUE_TYPE = "number"
    PARAMS = JsonSubsetParams

    def measure(self, context: MetricContext) -> MetricResult:
        expected = DottedPath(f"output.{self.params.path}").value_in(context.case.expected)
        if not isinstance(expected, dict) or not expected:
            return MetricResult(value=None, details={"reason": "the case expects no fields at this path"})
        actual_root = DottedPath(self.params.path).value_in(context.trace.output or {})
        leaves = self._leaf_values_by_path(expected)
        wrong = {}
        for path, wanted in leaves.items():
            actual = DottedPath(path).value_in(actual_root) if actual_root is not MISSING else MISSING
            matcher = ValueMatcher(self.params.modes.get(path, "exact"), self.params.coerce)
            if actual is MISSING or not matcher.matches(actual, wanted):
                wrong[path] = {"expected": wanted, "actual": None if actual is MISSING else actual}
        return MetricResult(value=(len(leaves) - len(wrong)) / len(leaves), details={"mismatched": wrong})

    @classmethod
    def _leaf_values_by_path(cls, value: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        leaves = {}
        for key, item in value.items():
            path = f"{prefix}{key}"
            leaves.update(
                cls._leaf_values_by_path(item, f"{path}.") if isinstance(item, dict) and item else {path: item}
            )
        return leaves
