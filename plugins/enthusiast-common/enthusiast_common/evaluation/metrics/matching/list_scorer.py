from typing import Any

from .dotted_path import MISSING, DottedPath
from .list_score import ListScore
from .value_matcher import ValueMatcher


class ListScorer:
    """Pairs actual list items with expected ones by key (exact matches first), then checks their fields."""

    def __init__(self, key: str | int | None = None, fields: dict[str | int, str] | None = None, coerce: bool = False):
        self.key = None if key is None else DottedPath(str(key))
        self.fields = {DottedPath(str(f)): ValueMatcher(spec, coerce) for f, spec in (fields or {}).items()}
        self.exact = ValueMatcher("exact", coerce)

    def score(self, actual: list[Any], expected: list[Any]) -> ListScore:
        """Matched counts plus missing, extra and mismatched items, for F1, precision and recall."""
        unpaired = list(actual)
        score = ListScore()
        unmatched = []
        for wanted in expected:
            index = next(
                (
                    i
                    for i, item in enumerate(unpaired)
                    if self._is_same_item(item, wanted) and not self._mismatched_fields(item, wanted)
                ),
                None,
            )
            if index is None:
                unmatched.append(wanted)
            else:
                unpaired.pop(index)
                score.matched += 1
        for wanted in unmatched:
            index = next((i for i, item in enumerate(unpaired) if self._is_same_item(item, wanted)), None)
            if index is None:
                score.missing.append(wanted)
            else:
                item = unpaired.pop(index)
                score.mismatched.append(
                    {"expected": wanted, "actual": item, "fields": self._mismatched_fields(item, wanted)}
                )
        score.extra.extend(unpaired)
        return score

    def _mismatched_fields(self, item: Any, wanted: Any) -> list[str]:
        return [
            path.path for path, matcher in self.fields.items() if not self._field_matches(matcher, path, item, wanted)
        ]

    def _is_same_item(self, item: Any, wanted: Any) -> bool:
        if self.key is None:
            return self.exact.matches(item, wanted)
        actual_key, expected_key = self.key.value_in(ValueMatcher.to_plain_value(item)), self.key.value_in(wanted)
        return actual_key is not MISSING and self.exact.matches(actual_key, expected_key)

    @staticmethod
    def _field_matches(matcher: ValueMatcher, path: DottedPath, item: Any, wanted: Any) -> bool:
        actual, expected = path.value_in(ValueMatcher.to_plain_value(item)), path.value_in(wanted)
        return expected is MISSING or (actual is not MISSING and matcher.matches(actual, expected))
