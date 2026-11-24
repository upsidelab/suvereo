from typing import Any

from pydantic import BaseModel, ConfigDict
from suvereo_common.evaluation.metrics.base_metric import BaseMetric
from suvereo_common.evaluation.metrics.matching import ArgumentFilter
from suvereo_common.evaluation.metrics.metric_context import MetricContext
from suvereo_common.evaluation.metrics.metric_result import MetricResult


class ToolCalledParams(BaseModel):
    """Settings for the tool called metric."""

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
        """Check whether the tool was called."""
        accepted = ArgumentFilter(self.params.args, self.params.coerce)
        calls = [c for c in context.trace.tool_calls_named(self.params.name) if accepted.matches_arguments(c.args)]
        return MetricResult(value=float(len(calls)))
