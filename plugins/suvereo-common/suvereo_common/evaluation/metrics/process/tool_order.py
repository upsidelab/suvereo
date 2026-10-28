from pydantic import BaseModel, ConfigDict, Field

from ..base_metric import BaseMetric
from ..metric_context import MetricContext
from ..metric_result import MetricResult


class ToolOrderParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: list[str] = Field(min_length=1)
    strict: bool = False


class ToolOrder(BaseMetric):
    """Whether the agent called tools in a given order: in sequence among other calls, or exactly that when strict."""

    NAME = "tool_order"
    VALUE_TYPE = "bool"
    PARAMS = ToolOrderParams

    def measure(self, context: MetricContext) -> MetricResult:
        called = [c.name for c in context.trace.tool_calls]
        if self.params.strict:
            in_order = called == self.params.sequence
        else:
            remaining = iter(called)
            in_order = all(name in remaining for name in self.params.sequence)
        return MetricResult(value=in_order, details={} if in_order else {"called": called})
