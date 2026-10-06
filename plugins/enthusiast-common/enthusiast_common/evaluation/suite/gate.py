from typing import Any

from pydantic import Field, model_validator

from .base import EvalModel


class Gate(EvalModel):
    """The threshold a metric's value must meet for a run to pass."""

    min: float | None = None
    max: float | None = None
    equals: Any = None
    in_: list[Any] | None = Field(default=None, alias="in")

    @model_validator(mode="after")
    def _has_a_condition(self) -> "Gate":
        if self.min is None and self.max is None and self.equals is None and self.in_ is None:
            raise ValueError("A gate needs at least one of 'min', 'max', 'equals' or 'in'.")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("A gate's 'min' is greater than its 'max'.")
        return self
