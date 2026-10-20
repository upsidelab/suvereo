from pydantic import BaseModel, ConfigDict

from ..base_metric import BaseMetric
from ..metric_context import MetricContext
from ..metric_result import MetricResult


class ToolNotCalledParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str


class ToolNotCalled(BaseMetric):
    """Whether the agent never called a tool."""

    NAME = "tool_not_called"
    VALUE_TYPE = "bool"
    PARAMS = ToolNotCalledParams

    def measure(self, context: MetricContext) -> MetricResult:
        return MetricResult(value=not context.trace.tool_calls_named(self.params.name))
