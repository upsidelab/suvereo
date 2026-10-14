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
