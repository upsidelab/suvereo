from ..metric_context import MetricContext
from .run_figure import RunFigure


class ToolCalls(RunFigure):
    """How many tool calls the agent made."""

    NAME = "tool_calls"

    def read_figure(self, context: MetricContext) -> int:
        return len(context.trace.tool_calls)
