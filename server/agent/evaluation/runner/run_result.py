from enthusiast_common.evaluation.metrics import MetricResult
from enthusiast_common.evaluation.trace import ExecutionTrace
from pydantic import BaseModel, Field


class GateResult(BaseModel):
    """Whether a metric's gate passed, and whether that decides the run."""

    passed: bool
    required: bool


class RunResult(BaseModel):
    """One run of one case, for one model, variant and repeat: its trace, metrics and verdict."""

    case_id: str
    model: str = Field(description="The model's label, or empty for the DataSet's configured model.")
    variant: str
    repeat: int
    passed: bool
    metrics: dict[str, MetricResult]
    gates: dict[str, GateResult]
    unpriced_models: list[str] = []
    trace: ExecutionTrace
