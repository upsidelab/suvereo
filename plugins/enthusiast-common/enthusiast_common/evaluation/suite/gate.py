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

    def passes(self, value: Any) -> bool:
        """Whether a value meets every condition; an unmeasured (None) value never does, nor a non-number a bound.

        A bool only ever equals a bool: in Python True == 1, which would let `equals: true` gate a count.
        """
        if value is None:
            return False
        if self.equals is not None and not self._same(value, self.equals):
            return False
        if self.in_ is not None and not any(self._same(value, option) for option in self.in_):
            return False
        if self.min is None and self.max is None:
            return True
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        return (self.min is None or value >= self.min) and (self.max is None or value <= self.max)

    @staticmethod
    def _same(value: Any, expected: Any) -> bool:
        return isinstance(value, bool) == isinstance(expected, bool) and value == expected
