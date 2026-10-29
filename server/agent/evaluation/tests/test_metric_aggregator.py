import pytest

from agent.evaluation.aggregation import MetricAggregate, MetricAggregator

from .aggregation_runs import run


class TestMetricAggregate:
    def test_numbers_skip_unmeasured_values(self):
        figures = MetricAggregate.from_values([1.0, 2.0, 3.0, 4.0, None], "number")

        assert (figures.measured, figures.value, figures.min, figures.max, figures.sum) == (4, 2.5, 1.0, 4.0, 10.0)
        assert (figures.p50, figures.p95) == (2.5, pytest.approx(3.85))

    def test_bools_default_to_their_rate(self):
        assert MetricAggregate.from_values([True, False, True, True], "bool").value == 0.75

    def test_labels_default_to_the_most_common(self):
        figures = MetricAggregate.from_values(["late", "ok", "late", None], "label")

        assert (figures.value, figures.distribution) == ("late", {"late": 2, "ok": 1})

    def test_a_declared_aggregate_picks_the_value(self):
        assert MetricAggregate.from_values([1.0, 10.0], "number", "max").value == 10.0
        assert MetricAggregate.from_values([None], "number").value is None

    @pytest.mark.parametrize(
        "values, value_type, aggregate",
        [([1.0], "number", "distribution"), (["late"], "label", "mean"), ([True], "bool", "distribution")],
    )
    def test_an_aggregate_that_does_not_fit_the_value_type_is_refused(self, values, value_type, aggregate):
        with pytest.raises(ValueError):
            MetricAggregate.from_values(values, value_type, aggregate)


class TestMetricAggregator:
    def test_groups_runs_by_candidate_with_components_and_rates(self):
        runs = [
            run("a", model="x", line_items=1.0, attempts=1.0, components={"precision": 1.0}),
            run("a", model="x", repeat=2, passed=False, line_items=0.5, attempts=2.0, components={"precision": 0.5}),
            run("b", model="x", line_items=1.0, attempts=2.0),
            run("a", model="y", line_items=0.0, attempts=1.0, passed=False),
        ]

        x, y = MetricAggregator({"line_items": "number"}).aggregate_per_candidate(runs)

        assert (x.candidate, len(x.runs), y.candidate) == ("x/default", 3, "y/default")
        assert x.metrics["line_items"].value == pytest.approx(2.5 / 3)
        assert x.metrics["line_items.precision"].value == 0.75
        assert x.metrics["pass_rate"].value == pytest.approx(2 / 3)
        assert x.metrics["first_attempt_pass_rate"].value == pytest.approx(1 / 3)
        assert x.metrics["flaky_rate"].value == 0.5

    def test_conversations_have_no_first_attempt_pass_rate(self):
        runs = [run("a", turns=2.0), run("b", passed=False, turns=3.0)]
        for conversation in runs:
            del conversation.metrics["attempts"]

        [candidate] = MetricAggregator({"turns": "number"}, kind="conversation").aggregate_per_candidate(runs)

        assert (candidate.metrics["pass_rate"].value, candidate.metrics["flaky_rate"].value) == (0.5, 0.0)
        assert "first_attempt_pass_rate" not in candidate.metrics
        assert candidate.metrics["turns"].value == 2.5
