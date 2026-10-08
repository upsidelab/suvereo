from ..metric_context import MetricContext
from .run_figure import RunFigure


class OutputTokens(RunFigure):
    """Output tokens over every LLM call in the run."""

    NAME = "output_tokens"

    def figure(self, context: MetricContext) -> int:
        return context.trace.output_tokens
