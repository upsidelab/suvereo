from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .mock_raise import MockRaise


class MockBehaviour(BaseModel):
    """What a mocked method does: return a value, return values in sequence, or raise, optionally only when matched."""

    model_config = ConfigDict(extra="forbid")

    returns: Any = Field(default=None, description="Strings are templates over {n}, {args}, {kwargs} and named args.")
    sequence: list[Any] | None = Field(default=None, description="One value per call; the last one repeats.")
    raises: MockRaise | None = None
    when: dict[str, Any] | None = Field(default=None, description="Applies only when these named arguments match.")
    latency_ms: float = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _exactly_one_outcome(self) -> "MockBehaviour":
        outcomes = ["returns" in self.model_fields_set, self.sequence is not None, self.raises is not None]
        if sum(outcomes) != 1:
            raise ValueError("Set exactly one of 'returns', 'sequence' or 'raises'; only 'returns' may be null.")
        if self.sequence is not None and not self.sequence:
            raise ValueError("'sequence' needs at least one value.")
        return self

    def matches(self, arguments: dict[str, Any]) -> bool:
        """Whether this behaviour applies to a call's named arguments; tuples equal lists and models equal their dumps."""
        if self.when is None:
            return True
        return all(
            name in arguments and self._plain(arguments[name]) == self._plain(value)
            for name, value in self.when.items()
        )

    @classmethod
    def _plain(cls, value: Any) -> Any:
        if isinstance(value, BaseModel):
            return cls._plain(value.model_dump())
        if isinstance(value, (list, tuple)):
            return [cls._plain(v) for v in value]
        if isinstance(value, dict):
            return {k: cls._plain(v) for k, v in value.items()}
        return value
