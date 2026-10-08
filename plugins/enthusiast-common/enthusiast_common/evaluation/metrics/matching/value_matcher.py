import re
from difflib import SequenceMatcher
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel

from ..errors import MetricConfigError

MODES = ("exact", "ci", "numeric", "fuzzy", "regex")
DEFAULT_FUZZY_THRESHOLD = 0.85


class ValueMatcher:
    """Compares values in a mode: exact, ci, numeric[:tolerance], fuzzy[:threshold] or regex; coerce makes exact compare numbers."""

    def __init__(self, spec: str = "exact", coerce: bool = False):
        """Parse a mode such as numeric:0.01; raises ValueError for an invalid one."""
        mode, _, argument = spec.partition(":")
        if mode not in MODES:
            raise ValueError(f"Unknown match mode '{mode}'; use one of {', '.join(MODES)}.")
        if argument and mode not in ("numeric", "fuzzy"):
            raise ValueError(f"Match mode '{mode}' takes no argument.")
        self.mode = mode
        self.coerce = coerce
        self.argument = float(argument) if argument else (DEFAULT_FUZZY_THRESHOLD if mode == "fuzzy" else 0.0)

    def matches(self, actual: Any, expected: Any) -> bool:
        """Whether the actual value matches the expected one in this mode."""
        actual, expected = self.plain(actual), self.plain(expected)
        if self.mode == "exact":
            if self._equal(actual, expected) or not self.coerce:
                return self._equal(actual, expected)
            number = self._number(actual)
            return number is not None and number == self._number(expected)
        if self.mode == "numeric":
            a, e = self._number(actual), self._number(expected)
            return a is not None and e is not None and abs(a - e) <= self.argument
        if self.mode == "regex":
            try:
                return actual is not None and re.fullmatch(str(expected), str(actual)) is not None
            except re.error as e:
                raise MetricConfigError(f"Expected value '{expected}' is not a valid regex: {e}") from e
        a, e = self._text(actual), self._text(expected)
        if self.mode == "ci":
            return a == e
        return SequenceMatcher(None, a, e).ratio() >= self.argument

    @classmethod
    def checked(cls, spec: str) -> str:
        """The spec unchanged if it parses; raises ValueError otherwise, for use as a Pydantic validator."""
        cls(spec)
        return spec

    @classmethod
    def plain(cls, value: Any) -> Any:
        """The value as YAML would write it: tuples become lists and Pydantic models their dumps."""
        if isinstance(value, BaseModel):
            return cls.plain(value.model_dump())
        if isinstance(value, (list, tuple)):
            return [cls.plain(v) for v in value]
        if isinstance(value, dict):
            return {k: cls.plain(v) for k, v in value.items()}
        return value

    @classmethod
    def _equal(cls, actual: Any, expected: Any) -> bool:
        if isinstance(actual, bool) != isinstance(expected, bool):
            return False
        if isinstance(actual, list) and isinstance(expected, list):
            return len(actual) == len(expected) and all(cls._equal(a, e) for a, e in zip(actual, expected))
        if isinstance(actual, dict) and isinstance(expected, dict):
            return actual.keys() == expected.keys() and all(cls._equal(actual[k], expected[k]) for k in actual)
        return actual == expected

    @staticmethod
    def _number(value: Any) -> float | None:
        if isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _text(value: Any) -> str:
        return " ".join(str(value).split()).casefold() if value is not None else ""


#: A match mode in metric params, checked when the suite loads rather than mid-run.
MatchMode = Annotated[str, AfterValidator(ValueMatcher.checked)]
