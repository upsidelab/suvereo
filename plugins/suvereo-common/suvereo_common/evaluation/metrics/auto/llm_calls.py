from suvereo_common.evaluation.metrics.auto.run_figure import RunFigure
from suvereo_common.evaluation.metrics.metric_context import MetricContext


class LLMCalls(RunFigure):
    """How many LLM calls the run made, nested ones included."""

    NAME = "llm_calls"

    def read_figure(self, context: MetricContext) -> int:
        return len(context.trace.llm_calls)
