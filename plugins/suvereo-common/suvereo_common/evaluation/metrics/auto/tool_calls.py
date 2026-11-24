from suvereo_common.evaluation.metrics.auto.run_figure import RunFigure
from suvereo_common.evaluation.metrics.metric_context import MetricContext


class ToolCalls(RunFigure):
    """How many tool calls the agent made."""

    NAME = "tool_calls"

    def read_figure(self, context: MetricContext) -> int:
        return len(context.trace.tool_calls)
