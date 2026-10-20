from typing import Any

from .value_matcher import ValueMatcher


class ArgumentFilter:
    """Decides which tool or mock calls a counting metric counts, by argument values (the metric's `args:`).

    A call is kept when every required argument is present with an equal value; arguments not listed are ignored.
    With no required values every call is kept. E.g. {"email": "a@b.c"} keeps create_order(items=[...], email="a@b.c").
    """

    def __init__(self, required: dict[str, Any] | None = None, coerce: bool = False):
        self.required = required or {}
        self.matcher = ValueMatcher("exact", coerce)

    def matches_arguments(self, arguments: dict[str, Any]) -> bool:
        """Whether a call's arguments include every required value."""
        return all(
            name in arguments and self.matcher.matches(arguments[name], value) for name, value in self.required.items()
        )
