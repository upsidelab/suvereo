from typing import Any

from pydantic import BaseModel


class ListScore(BaseModel):
    """How well actual list items matched the expected ones; an item with a wrong field counts as both missed and extra."""

    matched: int = 0
    missing: list[Any] = []
    extra: list[Any] = []
    mismatched: list[dict[str, Any]] = []

    @property
    def precision(self) -> float:
        found = self.matched + len(self.extra) + len(self.mismatched)
        return self.matched / found if found else 1.0

    @property
    def recall(self) -> float:
        wanted = self.matched + len(self.missing) + len(self.mismatched)
        return self.matched / wanted if wanted else 1.0

    @property
    def f1(self) -> float:
        errors = len(self.missing) + len(self.extra) + 2 * len(self.mismatched)
        return 2 * self.matched / (2 * self.matched + errors) if self.matched or errors else 1.0

    def combined_with(self, other: "ListScore") -> "ListScore":
        """This score and another added together, e.g. across several calls."""
        return ListScore(
            matched=self.matched + other.matched,
            missing=self.missing + other.missing,
            extra=self.extra + other.extra,
            mismatched=self.mismatched + other.mismatched,
        )
