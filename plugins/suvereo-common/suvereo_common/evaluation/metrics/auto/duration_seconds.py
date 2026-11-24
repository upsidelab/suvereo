from suvereo_common.evaluation.metrics.auto.run_figure import RunFigure
from suvereo_common.evaluation.metrics.metric_context import MetricContext


class DurationSeconds(RunFigure):
    """Wall-clock seconds the run took."""

    NAME = "duration_s"

    def read_figure(self, context: MetricContext) -> float | None:
        """Return the run's duration in seconds."""
        return context.duration_s
