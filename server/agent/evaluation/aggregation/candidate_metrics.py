from suvereo_common.evaluation.metrics.auto import CostUsd
from pydantic import BaseModel

from agent.evaluation.runner import RunResult

from .metric_aggregate import MetricAggregate


class CandidateMetrics(BaseModel):
    """Everything measured for one model x variant, aggregated over its runs."""

    candidate: str
    model: str
    variant: str
    runs: list[RunResult]
    metrics: dict[str, MetricAggregate]

    @property
    def cost_mean_usd(self) -> float | None:
        """The mean agent cost per run; None when no run could be priced."""
        cost = self.metrics.get(CostUsd.NAME)
        return cost.mean if cost else None
