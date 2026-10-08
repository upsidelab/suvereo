from ..metric_context import MetricContext
from .run_figure import RunFigure


class DurationSeconds(RunFigure):
    """Wall-clock seconds the run took."""

    NAME = "duration_s"

    def figure(self, context: MetricContext) -> float | None:
        return context.duration_s
