from typing import Any

from pydantic import BaseModel, ConfigDict

from ..base_metric import BaseMetric
from ..matching import ArgumentFilter
from ..metric_context import MetricContext
from ..metric_result import MetricResult


class MockCalledParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str
    args: dict[str, Any] = {}
    coerce: bool = False


class MockCalled(BaseMetric):
    """How many times a mocked method was called, optionally only with given argument values."""

    NAME = "mock_called"
    VALUE_TYPE = "number"
    PARAMS = MockCalledParams

    def measure(self, context: MetricContext) -> MetricResult:
        accepted = ArgumentFilter(self.params.args, self.params.coerce)
        calls = [c for c in context.trace.mock_calls_to(self.params.method) if accepted.accepts(c.arguments)]
        return MetricResult(value=float(len(calls)))
