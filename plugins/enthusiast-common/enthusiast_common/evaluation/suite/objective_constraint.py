from pydantic import model_validator

from .base import EvalModel
from .metric_config import Aggregate


class ObjectiveConstraint(EvalModel):
    """A hard limit; a candidate that breaks one is never ranked first."""

    metric: str
    min: float | None = None
    max: float | None = None
    aggregate: Aggregate | None = None

    @model_validator(mode="after")
    def _has_a_limit(self) -> "ObjectiveConstraint":
        if self.min is None and self.max is None:
            raise ValueError(f"Constraint on '{self.metric}' needs 'min' or 'max'.")
        return self
