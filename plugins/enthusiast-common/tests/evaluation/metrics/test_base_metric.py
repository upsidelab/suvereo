import pytest
from enthusiast_common.evaluation.metrics import (
    BaseMetric,
    MetricConfigError,
    MetricContext,
    MetricNotFoundError,
    MetricRegistry,
    MetricResult,
)
from enthusiast_common.evaluation.suite import EvalCase, MetricConfig
from enthusiast_common.evaluation.trace import Attempt, ExecutionTrace

from .sample_metrics import AttemptsAtMost


class TestBaseMetric:
    def test_params_are_validated_and_the_name_defaults_to_the_type(self):
        metric = AttemptsAtMost({"threshold": 2})

        assert metric.params.threshold == 2
        assert metric.name == "attempts_at_most"

    def test_invalid_params_are_reported_with_the_metric_name(self):
        with pytest.raises(MetricConfigError, match="'strict_attempts'"):
            AttemptsAtMost({"threshold": "many"}, name="strict_attempts")

    def test_a_metric_without_params_rejects_any(self):
        class Constant(BaseMetric):
            NAME = "constant"
            VALUE_TYPE = "number"

            def measure(self, context):
                return MetricResult(value=1.0)

        with pytest.raises(MetricConfigError):
            Constant({"unexpected": 1})

    def test_measures_a_run(self):
        trace = ExecutionTrace(attempts=[Attempt(number=1, response="{}", passed=True)])

        result = AttemptsAtMost({"threshold": 1}).measure(MetricContext(trace=trace, case=EvalCase(id="c")))

        assert result.value is True

    def test_an_intermediate_base_marked_abstract_needs_no_value_type(self):
        class TraceMetric(BaseMetric):
            __abstract__ = True

            def measure(self, context):
                return MetricResult(value=None)

        class ToolErrors(TraceMetric):
            NAME = "tool_errors"
            VALUE_TYPE = "number"

        assert ToolErrors().name == "tool_errors"

    @pytest.mark.parametrize(
        "namespace, message",
        [
            ({"VALUE_TYPE": "bool"}, "NAME"),
            ({"NAME": "x"}, "VALUE_TYPE"),
            ({"NAME": "x", "VALUE_TYPE": "percentage"}, "percentage"),
            ({"NAME": "x", "VALUE_TYPE": "bool", "KINDS": ("chat",)}, "chat"),
            ({"NAME": "x", "VALUE_TYPE": "bool", "KINDS": ()}, "KINDS"),
        ],
    )
    def test_a_concrete_metric_must_declare_its_contract(self, namespace, message):
        with pytest.raises(TypeError, match=message):
            type("Broken", (BaseMetric,), {**namespace, "measure": lambda self, context: None})


class TestMetricRegistry:
    def test_finds_builtins_by_name_and_custom_metrics_by_dotted_path(self):
        registry = MetricRegistry([AttemptsAtMost])

        assert registry.metric_class("attempts_at_most") is AttemptsAtMost
        assert registry.metric_class(f"{AttemptsAtMost.__module__}.AttemptsAtMost") is AttemptsAtMost

    @pytest.mark.parametrize("metric_type", ["no_such_metric", "json.dumps", "no.such.module.Metric"])
    def test_unknown_metrics_are_reported(self, metric_type):
        with pytest.raises(MetricNotFoundError):
            MetricRegistry([AttemptsAtMost]).metric_class(metric_type)

    def test_builds_a_configured_metric_under_its_suite_name(self):
        config = MetricConfig(type="attempts_at_most", name="few_attempts", params={"threshold": 3})

        metric = MetricRegistry([AttemptsAtMost]).build_metric(config)

        assert (metric.name, metric.params.threshold) == ("few_attempts", 3)
