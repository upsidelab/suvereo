from ..metric_context import MetricContext
from .run_figure import RunFigure


class InputTokens(RunFigure):
    """Input tokens over every LLM call in the run."""

    NAME = "input_tokens"

    def read_figure(self, context: MetricContext) -> int:
        return context.trace.input_tokens
