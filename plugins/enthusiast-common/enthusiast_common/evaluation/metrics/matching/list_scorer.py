from typing import Any

from .dotted_path import MISSING, DottedPath
from .list_score import ListScore
from .value_matcher import ValueMatcher


class ListScorer:
    """Pairs actual list items with expected ones by a key, then checks their other fields.

    Fully matching items are paired first, so repeated keys (the same SKU on two lines) pair the best way round.

    Args:
        key: The field or index identifying an item, e.g. ``sku`` or ``0``; without one, whole items are compared.
        fields: The fields to check on paired items, each with its match mode.
        coerce: Treat number-like text as numbers when comparing keys and exact fields.
    """

    def __init__(self, key: str | int | None = None, fields: dict[str | int, str] | None = None, coerce: bool = False):
        self.key = None if key is None else DottedPath(str(key))
        self.fields = {DottedPath(str(f)): ValueMatcher(spec, coerce) for f, spec in (fields or {}).items()}
        self.exact = ValueMatcher("exact", coerce)

    def score(self, actual: list[Any], expected: list[Any]) -> ListScore:
        """Score actual items against the expected ones.

        Args:
            actual: What the agent produced.
            expected: What the case expects.

        Returns:
            Matched counts and the missing, extra and mismatched items, for F1, precision and recall.
        """
        unpaired = list(actual)
        score = ListScore()
        unmatched = []
        for wanted in expected:
            index = next(
                (
                    i
                    for i, item in enumerate(unpaired)
                    if self._same_item(item, wanted) and not self._wrong_fields(item, wanted)
                ),
                None,
            )
            if index is None:
                unmatched.append(wanted)
            else:
                unpaired.pop(index)
                score.matched += 1
        for wanted in unmatched:
            index = next((i for i, item in enumerate(unpaired) if self._same_item(item, wanted)), None)
            if index is None:
                score.missing.append(wanted)
            else:
                item = unpaired.pop(index)
                score.mismatched.append(
                    {"expected": wanted, "actual": item, "fields": self._wrong_fields(item, wanted)}
                )
        score.extra.extend(unpaired)
        return score

    def _wrong_fields(self, item: Any, wanted: Any) -> list[str]:
        return [
            path.path for path, matcher in self.fields.items() if not self._field_matches(matcher, path, item, wanted)
        ]

    def _same_item(self, item: Any, wanted: Any) -> bool:
        if self.key is None:
            return self.exact.matches(item, wanted)
        actual_key, expected_key = self.key.get(ValueMatcher.plain(item)), self.key.get(wanted)
        return actual_key is not MISSING and self.exact.matches(actual_key, expected_key)

    @staticmethod
    def _field_matches(matcher: ValueMatcher, path: DottedPath, item: Any, wanted: Any) -> bool:
        actual, expected = path.get(ValueMatcher.plain(item)), path.get(wanted)
        return expected is MISSING or (actual is not MISSING and matcher.matches(actual, expected))
