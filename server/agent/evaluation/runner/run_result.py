from pydantic import BaseModel, Field
from suvereo_common.evaluation.metrics import MetricResult
from suvereo_common.evaluation.trace import ExecutionTrace

DEFAULT_MODEL = "default"


class ThresholdResult(BaseModel):
    passed: bool
    required: bool


class RunResult(BaseModel):
    case_id: str
    model: str = Field(description="The model's label, or empty for the DataSet's configured model.")
    variant: str
    repeat: int
    passed: bool
    metrics: dict[str, MetricResult]
    thresholds: dict[str, ThresholdResult]
    unpriced_models: list[str] = Field(default=[], description="Models of calls that could not be priced.")
    priced_spend_usd: float = Field(default=0.0, description="USD of every call in the run that could be priced.")
    trace: ExecutionTrace

    @property
    def candidate(self) -> str:
        return f"{self.model or DEFAULT_MODEL}/{self.variant}"
