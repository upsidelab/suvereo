import pytest
from suvereo_common.evaluation.metrics import MetricConfigError
from suvereo_common.evaluation.metrics.matching import MISSING, DottedPath, ListScorer, ValueMatcher


class TestDottedPath:
    def test_follows_dicts_and_list_indexes(self):
        assert DottedPath("items.1.sku").value_in({"items": [{"sku": "a"}, {"sku": "b"}]}) == "b"
        assert DottedPath("").value_in({"a": 1}) == {"a": 1}

    @pytest.mark.parametrize("path", ["missing", "items.5", "items.x", "items.0.sku.deeper"])
    def test_reports_missing_values(self, path):
        assert DottedPath(path).value_in({"items": [{"sku": "a"}]}) is MISSING


class TestValueMatcher:
    @pytest.mark.parametrize(
        "spec, actual, expected, matches",
        [
            ("exact", ("SKU-1", 2), ["SKU-1", 2], True),
            ("exact", "2", 2, False),
            ("exact", True, 1, False),
            ("exact", [True], [1], False),
            ("ci", "  Red   Mug ", "red mug", True),
            ("numeric", "2.0", 2, True),
            ("numeric:0.1", 2.05, 2, True),
            ("numeric:0.01", 2.05, 2, False),
            ("numeric", "two", 2, False),
            ("fuzzy", "Stainless steel mug", "Stainless-steel mug", True),
            ("fuzzy:0.99", "Stainless steel mug", "Steel mug", False),
            ("regex", "ORD-42", r"ORD-\d+", True),
            ("regex", "xORD-42", r"ORD-\d+", False),
        ],
    )
    def test_compares_in_each_mode(self, spec, actual, expected, matches):
        assert ValueMatcher(spec).matches(actual, expected) is matches

    def test_an_invalid_expected_regex_is_reported_as_configuration(self):
        with pytest.raises(MetricConfigError, match=r"\[A-Z"):
            ValueMatcher("regex").matches("ORD-1", "[A-Z")

    def test_coerce_compares_number_like_text_as_numbers(self):
        assert ValueMatcher("exact", coerce=True).matches("2", 2)
        assert not ValueMatcher("exact", coerce=True).matches(True, 1)

    @pytest.mark.parametrize("spec", ["exactly", "exact:1", "numeric:many"])
    def test_rejects_invalid_modes(self, spec):
        with pytest.raises(ValueError):
            ValueMatcher(spec)


class TestListScorer:
    def test_pairs_items_by_key_and_checks_fields(self):
        scorer = ListScorer(key=0, fields={1: "numeric"}, coerce=True)

        score = scorer.score(
            actual=[("SKU-1", "2"), ("SKU-7", "3"), ("SKU-9", "1")],
            expected=[["SKU-1", 2], ["SKU-7", 10], ["SKU-3", 5]],
        )

        assert score.matched == 1
        assert score.missing == [["SKU-3", 5]]
        assert score.extra == [("SKU-9", "1")]
        assert score.mismatched[0]["fields"] == ["1"]
        assert (score.precision, score.recall, score.f1) == (1 / 3, 1 / 3, pytest.approx(1 / 3))

    def test_repeated_keys_pair_the_best_way_round(self):
        score = ListScorer(key="sku", fields={"qty": "exact"}).score(
            actual=[{"sku": "A", "qty": 2}, {"sku": "A", "qty": 1}],
            expected=[{"sku": "A", "qty": 1}, {"sku": "A", "qty": 2}],
        )

        assert score.f1 == 1.0

    def test_repeated_keys_with_one_wrong_line_count_one_mismatch(self):
        score = ListScorer(key="sku", fields={"qty": "exact"}).score(
            actual=[{"sku": "A", "qty": 3}, {"sku": "A", "qty": 1}],
            expected=[{"sku": "A", "qty": 1}, {"sku": "A", "qty": 2}],
        )

        assert (score.matched, len(score.mismatched)) == (1, 1)
        assert score.mismatched[0]["actual"] == {"sku": "A", "qty": 3}

    def test_pairs_dict_items_by_named_key(self):
        score = ListScorer(key="sku").score([{"sku": "a", "qty": 1}], [{"sku": "a", "qty": 2}])

        assert score.matched == 1

    def test_without_a_key_compares_whole_items(self):
        assert ListScorer().score(["a", "b"], ["b", "a"]).f1 == 1.0

    def test_two_empty_lists_are_a_perfect_match(self):
        assert ListScorer().score([], []).f1 == 1.0
