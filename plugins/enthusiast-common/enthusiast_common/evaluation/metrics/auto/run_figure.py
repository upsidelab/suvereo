from abc import abstractmethod

from ..base_metric import BaseMetric
from ..metric_context import MetricContext
from ..metric_result import MetricResult


class RunFigure(BaseMetric):
    """A number read straight off the run; None when the run does not have it (e.g. a model without pricing)."""

    __abstract__ = True

    VALUE_TYPE = "number"

    def measure(self, context: MetricContext) -> MetricResult:
        value = self.figure(context)
        return MetricResult(value=None if value is None else float(value))

    @abstractmethod
    def figure(self, context: MetricContext) -> float | int | None:
        """The figure for one run."""
