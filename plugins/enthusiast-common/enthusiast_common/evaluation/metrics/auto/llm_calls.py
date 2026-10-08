from ..metric_context import MetricContext
from .run_figure import RunFigure


class LLMCalls(RunFigure):
    """How many LLM calls the run made, nested ones included."""

    NAME = "llm_calls"

    def figure(self, context: MetricContext) -> int:
        return len(context.trace.llm_calls)
