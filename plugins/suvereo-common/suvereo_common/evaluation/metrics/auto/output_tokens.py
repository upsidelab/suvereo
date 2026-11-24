from suvereo_common.evaluation.metrics.auto.run_figure import RunFigure
from suvereo_common.evaluation.metrics.metric_context import MetricContext


class OutputTokens(RunFigure):
    """Output tokens over every LLM call in the run."""

    NAME = "output_tokens"

    def read_figure(self, context: MetricContext) -> int:
        return context.trace.output_tokens
