from typing import Any, Literal

from pydantic import Field, model_validator

from .base import EvalModel
from .gate import Gate

Aggregate = Literal["mean", "rate", "sum", "min", "max", "p50", "p95", "distribution"]


class MetricConfig(EvalModel):
    """A metric measured on every run it applies to."""

    type: str = Field(description="A built-in metric's NAME, or a dotted path to a BaseMetric.")
    name: str = Field(default="", description="Names this instance in reports; defaults to type.")
    params: dict[str, Any] = {}
    gate: Gate | None = None
    required: bool = Field(default=True, description="False reports a failed gate as a warning only.")
    aggregate: Aggregate | None = None

    @model_validator(mode="after")
    def _default_name(self) -> "MetricConfig":
        if not self.name:
            self.name = self.type
        return self
