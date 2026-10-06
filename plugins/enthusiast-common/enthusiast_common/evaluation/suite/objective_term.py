from typing import Literal

from pydantic import Field, model_validator

from .base import EvalModel
from .metric_config import Aggregate


class ObjectiveTerm(EvalModel):
    """One weighted metric in the objective score."""

    metric: str = Field(description="A metric name, or 'metric.component' such as one judge criterion.")
    weight: float = Field(default=1.0, gt=0)
    direction: Literal["maximize", "minimize"] = "maximize"
    bounds: tuple[float, float] | None = Field(default=None, description="[best, worst] for unbounded metrics.")
    aggregate: Aggregate | None = None

    @model_validator(mode="after")
    def _bounds_differ(self) -> "ObjectiveTerm":
        if self.bounds is not None and self.bounds[0] == self.bounds[1]:
            raise ValueError(f"'{self.metric}' bounds must differ; equal bounds cannot normalise a value.")
        return self
