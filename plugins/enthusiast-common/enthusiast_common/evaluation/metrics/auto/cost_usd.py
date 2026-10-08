from ..metric_context import MetricContext
from .run_figure import RunFigure


class CostUsd(RunFigure):
    """What the run's LLM calls cost in USD, nested ones included."""

    NAME = "cost_usd"

    def figure(self, context: MetricContext) -> float | None:
        return context.cost_usd
