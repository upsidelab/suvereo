from suvereo_common.evaluation.metrics.auto.run_figure import RunFigure
from suvereo_common.evaluation.metrics.metric_context import MetricContext


class InputTokens(RunFigure):
    """Input tokens over every LLM call in the run."""

    NAME = "input_tokens"

    def read_figure(self, context: MetricContext) -> int:
        """Return the run's input tokens."""
        return context.trace.input_tokens
