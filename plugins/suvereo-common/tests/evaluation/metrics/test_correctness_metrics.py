import json

import pytest
from suvereo_common.evaluation.metrics import MetricConfigError, MetricRegistry
from suvereo_common.evaluation.metrics.correctness import FieldMatch, JsonSchema, JsonSubset, ListMatch, MockCalls
from suvereo_common.evaluation.suite import MetricConfig

from .contexts import mock_call, run

ORDER = {"order_id": "ORD-1", "customer": {"email": "A@B.c", "city": "Krakow"}, "total": 12.5}


class TestFieldMatch:
    def test_matches_an_output_field_in_the_given_mode(self):
        context = run(output=ORDER, expected={"output": {"customer": {"email": "a@b.c"}}})

        assert FieldMatch({"path": "customer.email", "mode": "ci"}).measure(context).value is True
        assert FieldMatch({"path": "customer.email"}).measure(context).details == {
            "expected": "a@b.c",
            "actual": "A@B.c",
        }

    def test_is_not_measured_when_the_case_expects_nothing_there(self):
        assert FieldMatch({"path": "order_id"}).measure(run(output=ORDER)).value is None

    def test_fails_when_the_output_lacks_the_field(self):
        assert (
            FieldMatch({"path": "order_id"}).measure(run(output={}, expected={"output": {"order_id": "x"}})).value
            is False
        )

    def test_an_invalid_mode_fails_when_the_suite_loads(self):
        with pytest.raises(MetricConfigError):
            FieldMatch({"path": "order_id", "mode": "nearly"})


class TestJsonSubset:
    def test_scores_the_share_of_expected_fields_matched(self):
        expected = {"output": {"order_id": "ORD-1", "customer": {"email": "a@b.c", "city": "Warsaw"}, "total": 12.5}}

        result = JsonSubset({"modes": {"customer.email": "ci"}}).measure(run(output=ORDER, expected=expected))

        assert result.value == 0.75
        assert list(result.details["mismatched"]) == ["customer.city"]


class TestListMatch:
    def test_scores_an_output_list_with_precision_and_recall(self):
        output = {"lines": [{"sku": "a", "qty": 1}, {"sku": "b", "qty": 2}]}
        expected = {"output": {"lines": [{"sku": "a", "qty": 1}, {"sku": "c", "qty": 1}]}}

        result = ListMatch({"path": "lines", "key": "sku", "fields": {"qty": "numeric"}}).measure(
            run(output=output, expected=expected)
        )

        assert result.value == 0.5
        assert result.components == {"precision": 0.5, "recall": 0.5}
        assert result.details["missing"] == [{"sku": "c", "qty": 1}]


class TestMockCalls:
    PARAMS = {"method": "create_order_with_items", "arg": "items", "key": 0, "fields": {1: "numeric"}, "coerce": True}

    def test_scores_order_lines_the_agent_sent_against_the_expected_ones(self):
        context = run(
            expected={"mock_calls": {"create_order_with_items": [{"items": [["SKU-1", 2], ["SKU-7", 10]]}]}},
            mock_calls=[mock_call("create_order_with_items", items=[("SKU-1", "2"), ("SKU-7", "10")], email=None)],
        )

        assert MockCalls(self.PARAMS).measure(context).value == 1.0

    def test_a_second_call_counts_its_items_as_extra(self):
        call = mock_call("create_order_with_items", items=[("SKU-1", "2")])
        context = run(
            expected={"mock_calls": {"create_order_with_items": [{"items": [["SKU-1", 2]]}]}}, mock_calls=[call, call]
        )

        result = MockCalls(self.PARAMS).measure(context)

        assert result.components["precision"] == 0.5
        assert result.details["calls"] == 2

    def test_skip_failed_leaves_out_a_rejected_call(self):
        rejected = mock_call("create_order_with_items", items=[("370", "2")]).model_copy(
            update={"error": "Unknown SKU"}
        )
        context = run(
            expected={"mock_calls": {"create_order_with_items": [{"items": [["SKU-1", 2]]}]}},
            mock_calls=[rejected, mock_call("create_order_with_items", items=[("SKU-1", "2")])],
        )

        assert MockCalls(self.PARAMS).measure(context).value == 0.0
        assert MockCalls({**self.PARAMS, "skip_failed": True}).measure(context).details["calls"] == 1
        assert MockCalls({**self.PARAMS, "skip_failed": True}).measure(context).value == 1.0

    def test_without_arg_scores_each_call_as_one_item_in_any_order(self):
        context = run(
            expected={"mock_calls": {"update_stock": [{"sku": "A", "quantity": 5}, {"sku": "B", "quantity": 2}]}},
            mock_calls=[mock_call("update_stock", sku="B", quantity=2), mock_call("update_stock", sku="A", quantity=4)],
        )

        result = MockCalls({"method": "update_stock", "key": "sku", "fields": {"quantity": "numeric"}}).measure(context)

        assert result.value == 0.5
        assert result.details["mismatched"][0]["fields"] == ["quantity"]

    def test_expecting_no_calls_fails_when_the_agent_made_one(self):
        context = run(
            expected={"mock_calls": {"create_order_with_items": []}},
            mock_calls=[mock_call("create_order_with_items", items=[("SKU-1", 1)])],
        )

        assert MockCalls(self.PARAMS).measure(context).value == 0.0

    def test_a_scalar_argument_counts_as_one_item(self):
        context = run(
            expected={"mock_calls": {"update_stock": [{"sku": "SKU-1"}]}},
            mock_calls=[mock_call("update_stock", sku="SKU-1", quantity=3)],
        )

        assert MockCalls({"method": "update_stock", "arg": "sku"}).measure(context).value == 1.0

    def test_a_malformed_expected_call_is_not_measured(self):
        context = run(expected={"mock_calls": {"create_order_with_items": [["SKU-1", 2]]}})

        result = MockCalls(self.PARAMS).measure(context)

        assert result.value is None
        assert "mapping" in result.details["reason"]

    def test_is_not_measured_when_the_case_expects_nothing_of_the_method(self):
        assert MockCalls(self.PARAMS).measure(run()).value is None


class TestJsonSchema:
    SCHEMA = {"type": "object", "required": ["order_id"], "properties": {"order_id": {"type": "string"}}}

    def test_validates_the_output_against_an_inline_schema(self):
        assert JsonSchema({"schema": self.SCHEMA}).measure(run(output=ORDER)).value is True

        result = JsonSchema({"schema": self.SCHEMA}).measure(run(output={"order_id": 1}))

        assert result.value is False
        assert result.details["errors"] == ["order_id: 1 is not of type 'string'"]

    def test_reads_a_schema_file(self, tmp_path):
        (tmp_path / "order.json").write_text(json.dumps(self.SCHEMA))

        assert JsonSchema({"schema_file": tmp_path / "order.json"}).measure(run(output={})).value is False

    def test_a_relative_schema_file_is_read_from_the_suite_directory(self, tmp_path, monkeypatch):
        (tmp_path / "schemas").mkdir()
        (tmp_path / "schemas" / "order.json").write_text(json.dumps(self.SCHEMA))
        monkeypatch.chdir("/")

        metric = MetricRegistry().build_metric(
            MetricConfig(type="json_schema", params={"schema_file": "schemas/order.json"}), tmp_path
        )

        assert metric.measure(run(output={"order_id": "ORD-1"})).value is True

    @pytest.mark.parametrize("params", [{}, {"schema": {"type": "nonsense"}}, {"schema_file": "/no/such/schema.json"}])
    def test_a_missing_or_invalid_schema_fails_when_the_suite_loads(self, params):
        with pytest.raises(MetricConfigError):
            JsonSchema(params)
