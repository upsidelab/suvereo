from typing import Any

from .value_matcher import ValueMatcher


class ArgumentFilter:
    """Selects calls whose named arguments include all of the given values; no values selects every call."""

    def __init__(self, required: dict[str, Any] | None = None, coerce: bool = False):
        self.required = required or {}
        self.matcher = ValueMatcher("exact", coerce)

    def matches_arguments(self, arguments: dict[str, Any]) -> bool:
        """Whether a call's arguments include every required value."""
        return all(
            name in arguments and self.matcher.matches(arguments[name], value) for name, value in self.required.items()
        )
