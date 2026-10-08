from typing import Any

from pydantic import BaseModel, ConfigDict

from ..base_metric import BaseMetric
from ..matching import ArgumentFilter
from ..metric_context import MetricContext
from ..metric_result import MetricResult


class ToolCalledParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    args: dict[str, Any] = {}
    coerce: bool = False


class ToolCalled(BaseMetric):
    """How many times the agent called a tool, optionally only with given argument values."""

    NAME = "tool_called"
    VALUE_TYPE = "number"
    PARAMS = ToolCalledParams

    def measure(self, context: MetricContext) -> MetricResult:
        accepted = ArgumentFilter(self.params.args, self.params.coerce)
        calls = [c for c in context.trace.tool_calls_named(self.params.name) if accepted.accepts(c.args)]
        return MetricResult(value=float(len(calls)))
