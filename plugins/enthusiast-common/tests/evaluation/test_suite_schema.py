import pytest
from enthusiast_common.evaluation.suite import EvalCase, EvalSuite, Gate, IntegrationConfig, MetricConfig
from pydantic import ValidationError

MINIMAL = {
    "agent": {"id": 12},
    "metrics": [{"type": "mock_calls", "gate": {"min": 0.95}}],
    "cases": "cases.csv",
}

FULL = {
    "name": "order-intake-ocr",
    "description": "OCR purchase orders into e-commerce orders",
    "agent": {"type": "enthusiast-agent-order-intake", "config": {}},
    "execution_key": "order-intake",
    "models": [
        {"provider": "OpenAI", "model": "gpt-4o"},
        {"provider": "Anthropic", "model": "claude-sonnet-5-5", "label": "sonnet"},
    ],
    "variants": [{"name": "v2", "system_prompt_file": "prompts/v2.txt"}],
    "judge": {"provider": "Anthropic", "model": "claude-opus-5-5"},
    "repeats": 3,
    "budget_usd": 5,
    "pass_threshold": 0.8,
    "integrations": [
        {
            "class": "enthusiast_ecommerce_common.evaluation.ECommerceMockIntegration",
            "config": {
                "catalog": "data/products.yaml",
                "behaviour": {"create_order_with_items": {"returns": "ORD-{n}"}},
            },
        }
    ],
    "metrics": [
        {
            "type": "mock_calls",
            "name": "line_items",
            "params": {"method": "create_order_with_items"},
            "gate": {"min": 0.95},
        },
        {"type": "tool_called", "name": "single_place_order", "params": {"name": "place_order"}, "gate": {"equals": 1}},
        {"type": "trace_event", "name": "retried", "params": {"event": "retry"}, "required": False},
    ],
    "objective": {
        "constraints": [{"metric": "pass_rate", "min": 0.9}],
        "score": [{"metric": "cost_usd", "weight": 0.15, "direction": "minimize", "bounds": [0, 0.1]}],
    },
    "cases": ["cases.csv", "cases/", {"id": "inline", "expected": {"output": {"order_id": "ORD-1"}}}],
}


def _suite(**changes) -> dict:
    return {**MINIMAL, **changes}


class TestEvalSuite:
    def test_the_minimal_suite_is_valid(self):
        suite = EvalSuite.model_validate(MINIMAL)

        assert suite.repeats == 1
        assert suite.models == []
        assert suite.metrics[0].name == "mock_calls"

    def test_the_full_suite_is_valid(self):
        suite = EvalSuite.model_validate(FULL)

        assert suite.integrations[0].class_path.endswith("ECommerceMockIntegration")
        assert suite.models[1].display_label == "sonnet"
        assert isinstance(suite.cases[2], EvalCase)

    def test_an_unknown_key_is_an_error_rather_than_ignored(self):
        with pytest.raises(ValidationError, match="repeat"):
            EvalSuite.model_validate(_suite(repeat=3))

    @pytest.mark.parametrize(
        "changes",
        [
            {"metrics": []},
            {"repeats": 0},
            {"pass_threshold": 1.5},
            {"agent": {"id": 1, "type": "x"}},
            {"agent": {}},
            {"agent": {"id": 1, "config": {"a": 1}}},
            {"variants": [{"name": "default", "system_prompt_file": "p.txt"}]},
            {"variants": [{"name": "empty"}]},
            {"objective": {"score": [{"metric": "cost_usd", "bounds": [0.1, 0.1]}]}},
        ],
    )
    def test_invalid_suites_are_rejected(self, changes):
        with pytest.raises(ValidationError):
            EvalSuite.model_validate(_suite(**changes))

    @pytest.mark.parametrize(
        "changes, kind",
        [
            ({"metrics": [{"type": "llm_judge"}, {"type": "llm_judge"}]}, "metric"),
            ({"variants": [{"name": "v", "agent_config": {"a": 1}}] * 2}, "variant"),
            ({"models": [{"provider": "OpenAI", "model": "gpt-4o"}] * 2}, "model label"),
        ],
    )
    def test_duplicate_names_are_rejected(self, changes, kind):
        with pytest.raises(ValidationError, match=f"Duplicate {kind}"):
            EvalSuite.model_validate(_suite(**changes))

    def test_integrations_for_replaces_the_behaviour_of_an_overridden_method(self):
        suite = EvalSuite.model_validate(FULL)
        case = EvalCase(
            id="raises",
            integrations=[
                IntegrationConfig.model_validate(
                    {
                        "class": suite.integrations[0].class_path,
                        "config": {"behaviour": {"create_order_with_items": {"raises": {"error": "X"}}}},
                    }
                ),
                IntegrationConfig(interface="crm.CrmPlugin"),
            ],
        )

        merged = suite.integrations_for(case)

        assert merged[0].config["catalog"] == "data/products.yaml"
        assert merged[0].config["behaviour"]["create_order_with_items"] == {"raises": {"error": "X"}}
        assert merged[1].interface == "crm.CrmPlugin"
        assert suite.integrations[0].config["behaviour"]["create_order_with_items"] == {"returns": "ORD-{n}"}

    def test_integrations_for_deep_merges_everything_but_behaviour(self):
        suite = EvalSuite.model_validate(
            _suite(
                integrations=[
                    {
                        "class": "mocks.Shop",
                        "config": {
                            "data": {"catalog": "a.yaml", "currency": "EUR"},
                            "behaviour": {"create_order": {"returns": "ORD-{n}"}, "get_product": {"returns": None}},
                        },
                    }
                ]
            )
        )
        case = EvalCase.model_validate(
            {"id": "c", "integrations": [{"class": "mocks.Shop", "config": {"data": {"currency": "USD"}}}]}
        )

        config = suite.integrations_for(case)[0].config

        assert config["data"] == {"catalog": "a.yaml", "currency": "USD"}
        assert config["behaviour"] == {"create_order": {"returns": "ORD-{n}"}, "get_product": {"returns": None}}

    def test_metrics_for_replaces_by_name_and_appends_new_ones(self):
        suite = EvalSuite.model_validate(FULL)
        case = EvalCase(
            id="c",
            metrics=[
                MetricConfig(type="mock_calls", name="line_items"),
                MetricConfig(type="trace_event", name="stopped"),
            ],
        )

        metrics = suite.metrics_for(case)

        assert [m.name for m in metrics] == ["line_items", "single_place_order", "retried", "stopped"]
        assert metrics[0].gate is None


class TestGate:
    def test_a_gate_needs_a_condition(self):
        with pytest.raises(ValidationError):
            Gate()

    def test_min_cannot_exceed_max(self):
        with pytest.raises(ValidationError):
            Gate(min=1, max=0)

    def test_in_is_written_as_in(self):
        assert Gate.model_validate({"in": ["a", "b"]}).in_ == ["a", "b"]


class TestIntegrationConfig:
    def test_needs_exactly_one_of_class_or_interface(self):
        with pytest.raises(ValidationError):
            IntegrationConfig.model_validate({"class": "a.B", "interface": "a.C"})
