from typing import Any

from pydantic import Field, model_validator

from .base import EvalModel


class PassThreshold(EvalModel):
    """The threshold a metric's value must meet for a run to pass."""

    min: float | None = None
    max: float | None = None
    equals: Any = None
    in_: list[Any] | None = Field(default=None, alias="in")

    @model_validator(mode="after")
    def _has_one_kind_of_condition(self) -> "PassThreshold":
        kinds = [self.equals is not None, self.in_ is not None, self.min is not None or self.max is not None]
        if sum(kinds) != 1:
            raise ValueError("A pass threshold needs exactly one of 'equals', 'in', or 'min'/'max'.")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("A pass threshold's 'min' is greater than its 'max'.")
        return self

    def passes(self, value: Any) -> bool:
        """Whether a value meets the condition; an unmeasured (None) value never does, nor a non-number a bound.

        A bool only ever equals a bool: in Python True == 1, which would let `equals: true` pass a count.
        """
        if value is None:
            return False
        if self.equals is not None:
            return self._strictly_equal(value, self.equals)
        if self.in_ is not None:
            return any(self._strictly_equal(value, option) for option in self.in_)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        return (self.min is None or value >= self.min) and (self.max is None or value <= self.max)

    @staticmethod
    def _strictly_equal(value: Any, expected: Any) -> bool:
        return isinstance(value, bool) == isinstance(expected, bool) and value == expected
