from suvereo_common.evaluation.metrics.auto.run_figure import RunFigure
from suvereo_common.evaluation.metrics.metric_context import MetricContext


class CostUsd(RunFigure):
    """What the run's LLM calls cost in USD, nested ones included."""

    NAME = "cost_usd"

    def read_figure(self, context: MetricContext) -> float | None:
        """Return the run's cost in USD, or None without pricing."""
        return context.cost_usd
