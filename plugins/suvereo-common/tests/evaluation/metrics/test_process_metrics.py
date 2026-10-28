import pytest
from suvereo_common.agentic_execution import StopExecutionValidator
from suvereo_common.evaluation.metrics import MetricConfigError
from suvereo_common.evaluation.metrics.process import MockCalled, ToolCalled, ToolNotCalled, ToolOrder, TraceEvent
from suvereo_common.evaluation.trace import Attempt, ToolCall

from .contexts import mock_call, run


def _tools(*names, errors=()):
    return [
        ToolCall(run_id=f"t{i}", name=n, args={"sku": f"SKU-{i}"}, error="E" if i in errors else None)
        for i, n in enumerate(names)
    ]


class TestToolMetrics:
    def test_tool_called_counts_calls_optionally_filtered_by_arguments(self):
        context = run(tool_calls=_tools("search", "place_order", "search"))

        assert ToolCalled({"name": "search"}).measure(context).value == 2.0
        assert ToolCalled({"name": "search", "args": {"sku": "SKU-2"}}).measure(context).value == 1.0

    def test_tool_not_called(self):
        context = run(tool_calls=_tools("search"))

        assert ToolNotCalled({"name": "place_order"}).measure(context).value is True
        assert ToolNotCalled({"name": "search"}).measure(context).value is False

    @pytest.mark.parametrize(
        "params, in_order",
        [
            ({"sequence": ["search", "place_order"]}, True),
            ({"sequence": ["place_order", "search"]}, False),
            ({"sequence": ["search", "lookup", "place_order"], "strict": True}, True),
            ({"sequence": ["search", "place_order"], "strict": True}, False),
        ],
    )
    def test_tool_order(self, params, in_order):
        context = run(tool_calls=_tools("search", "lookup", "place_order"))

        assert ToolOrder(params).measure(context).value is in_order


class TestMockCalled:
    def test_counts_calls_to_a_mocked_method_matching_arguments(self):
        context = run(
            mock_calls=[mock_call("update_stock", sku="SKU-1", quantity="3"), mock_call("update_stock", sku="SKU-2")]
        )

        assert MockCalled({"method": "update_stock"}).measure(context).value == 2.0
        assert (
            MockCalled({"method": "update_stock", "args": {"quantity": 3}, "coerce": True}).measure(context).value
            == 1.0
        )


class TestTraceEvent:
    @pytest.mark.parametrize(
        "event, happened",
        [
            ("retry", True),
            ("tool_error", True),
            ("validator_failed", True),
            ("validator_failed:MISSING_SKU", True),
            ("validator_failed:OTHER", False),
            ("stop_execution", False),
        ],
    )
    def test_reports_what_happened(self, event, happened):
        attempts = [
            Attempt(number=1, response="", passed=False, failure_code="MISSING_SKU"),
            Attempt(number=2, response="", passed=True),
        ]
        context = run(attempts=attempts, tool_calls=_tools("place_order", errors=(0,)))

        assert TraceEvent({"event": event}).measure(context).value is happened

    def test_stop_execution_is_the_stop_tool_being_called(self):
        context = run(tool_calls=_tools(StopExecutionValidator.TOOL_NAME))

        assert TraceEvent({"event": "stop_execution"}).measure(context).value is True

    @pytest.mark.parametrize(
        "event, in_conversations",
        [("tool_error", True), ("retry", False), ("validator_failed:MISSING_SKU", False), ("stop_execution", False)],
    )
    def test_only_tool_errors_can_be_checked_in_a_conversation(self, event, in_conversations):
        metric = TraceEvent({"event": event})

        assert metric.supports("execution")
        assert metric.supports("conversation") is in_conversations

    @pytest.mark.parametrize("event", ["crashed", "retry:3"])
    def test_unknown_events_fail_when_the_suite_loads(self, event):
        with pytest.raises(MetricConfigError):
            TraceEvent({"event": event})
