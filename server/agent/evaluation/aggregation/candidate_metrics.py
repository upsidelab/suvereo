from pydantic import BaseModel
from suvereo_common.evaluation.metrics.auto import CostUsd

from agent.evaluation.aggregation.metric_aggregate import MetricAggregate
from agent.evaluation.runner import RunResult


class CandidateMetrics(BaseModel):
    candidate: str
    model: str
    variant: str
    runs: list[RunResult]
    metrics: dict[str, MetricAggregate]

    @property
    def cost_mean_usd(self) -> float | None:
        cost = self.metrics.get(CostUsd.NAME)
        return cost.mean if cost else None
