import math
from collections import Counter
from statistics import mean, pstdev
from typing import Any

from pydantic import BaseModel
from suvereo_common.evaluation.suite import Aggregate

#: Aggregate names that read another figure: a bool's rate is its mean.
NUMBER_AGGREGATES = {"rate": "mean"}
DEFAULT_AGGREGATE_NAMES = {"number": "mean", "bool": "rate", "label": "most_common"}


class MetricAggregate(BaseModel):
    """One metric over a candidate's runs: the default aggregate as value, plus the figures reports show."""

    value_type: str
    measured: int
    value: float | str | None
    mean: float | None = None
    min: float | None = None
    max: float | None = None
    sum: float | None = None
    p50: float | None = None
    p95: float | None = None
    std: float | None = None
    distribution: dict[str, int] = {}

    @classmethod
    def from_values(cls, values: list[Any], value_type: str, aggregate: Aggregate | None = None) -> "MetricAggregate":
        """Compute mean, min, max, sum, percentiles (or label counts) from one metric's per-run values; skips None."""
        present = [v for v in values if v is not None]
        if value_type == "label":
            if aggregate not in (None, "distribution"):
                raise ValueError(f"A label metric has no '{aggregate}'; use distribution.")
            distribution = dict(Counter(str(v) for v in present).most_common())
            return cls(
                value_type=value_type,
                measured=len(present),
                value=next(iter(distribution), None),
                distribution=distribution,
            )
        numbers = sorted(float(v) for v in present)
        if aggregate == "distribution":
            raise ValueError("Only label metrics have a distribution.")
        figures = cls._figures(numbers) if numbers else {}
        value = figures.get(cls._figure_name(aggregate))
        return cls(value_type=value_type, measured=len(numbers), value=value, **figures)

    def value_for(self, aggregate: Aggregate | None = None) -> float | str | None:
        """The value under an aggregate: the top label for labels; for numbers and bools the mean (a bool's rate) by
        default. Raises ValueError for an aggregate that doesn't fit the value type, e.g. distribution of numbers."""
        if self.value_type == "label":
            if aggregate not in (None, "distribution"):
                raise ValueError(f"A label metric has no '{aggregate}'; use distribution.")
            return next(iter(self.distribution), None)
        if aggregate == "distribution":
            raise ValueError("Only label metrics have a distribution.")
        return getattr(self, self._figure_name(aggregate))

    @staticmethod
    def _figure_name(aggregate: Aggregate | None) -> str:
        name = aggregate or "mean"
        return NUMBER_AGGREGATES.get(name, name)

    @classmethod
    def _figures(cls, numbers: list[float]) -> dict[str, float]:
        return {
            "mean": mean(numbers),
            "min": numbers[0],
            "max": numbers[-1],
            "sum": sum(numbers),
            "p50": cls._percentile(numbers, 0.5),
            "p95": cls._percentile(numbers, 0.95),
            "std": pstdev(numbers),
        }

    @staticmethod
    def _percentile(numbers: list[float], q: float) -> float:
        position = q * (len(numbers) - 1)
        low, high = math.floor(position), math.ceil(position)
        return numbers[low] + (numbers[high] - numbers[low]) * (position - low)
