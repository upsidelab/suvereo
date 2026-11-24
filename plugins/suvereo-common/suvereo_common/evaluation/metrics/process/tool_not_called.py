from pydantic import BaseModel, ConfigDict
from suvereo_common.evaluation.metrics.base_metric import BaseMetric
from suvereo_common.evaluation.metrics.metric_context import MetricContext
from suvereo_common.evaluation.metrics.metric_result import MetricResult


class ToolNotCalledParams(BaseModel):
    """Settings for the tool not called metric."""

    model_config = ConfigDict(extra="forbid")

    name: str


class ToolNotCalled(BaseMetric):
    """Whether the agent never called a tool."""

    NAME = "tool_not_called"
    VALUE_TYPE = "bool"
    PARAMS = ToolNotCalledParams

    def measure(self, context: MetricContext) -> MetricResult:
        """Check that the tool was not called."""
        return MetricResult(value=not context.trace.tool_calls_named(self.params.name))
