from unittest.mock import patch

import pytest
import yaml
from enthusiast_common.evaluation.errors import EvalSuiteError

from agent.agentic_execution.registry import AgenticExecutionDefinitionRegistry
from agent.core.registries.agents.agent_registry import AgentNotFoundError, AgentRegistry
from agent.evaluation.judge_models_used_by_metrics import judge_models_used_by_metrics
from agent.evaluation.suite_loader import SuiteLoader

from .greeter import GreeterMockIntegration, GreetingExecution

pytestmark = pytest.mark.django_db

GREETER = f"{GreeterMockIntegration.__module__}.GreeterMockIntegration"


@pytest.fixture(autouse=True)
def _registered():
    with (
        patch.object(AgenticExecutionDefinitionRegistry, "get_all", return_value=[GreetingExecution]),
        patch.object(AgentRegistry, "get_agent_class_by_type", return_value=object),
    ):
        yield


def _load(tmp_path, **changes):
    suite = {
        "agent": {"type": "greeter-agent"},
        "models": [{"provider": "OpenAI", "model": "gpt-4o"}],
        "integrations": [{"class": GREETER, "config": {"behaviour": {"greet": {"returns": "Hi"}}}}],
        "metrics": [{"type": "mock_called", "params": {"method": "greet"}}],
        "cases": [{"id": "ada", "input": {"name": "Ada"}}],
        **changes,
    }
    path = tmp_path / "suite.yaml"
    path.write_text(yaml.safe_dump(suite))
    return SuiteLoader().load(path)


class TestSuiteLoader:
    def test_an_unregistered_sandbox_agent_type_fails_early(self, tmp_path):
        unknown = AgentNotFoundError("Could not find agent type 'greeter-agent'.")

        with patch.object(AgentRegistry, "get_agent_class_by_type", side_effect=unknown):
            with pytest.raises(EvalSuiteError, match="add it to AVAILABLE_AGENTS"):
                _load(tmp_path)

    def test_resolves_the_agent_types_only_execution(self, tmp_path):
        loaded = _load(tmp_path)

        assert loaded.suite.execution_key == "greeting"
        assert [case.id for case in loaded.cases] == ["ada"]

    @pytest.mark.parametrize(
        "changes, message",
        [
            ({"agent": {"type": "unknown-agent"}}, "has 0 registered executions"),
            ({"agent": {"id": 999}}, "no agent with id 999"),
            ({"execution_key": "farewell"}, "no execution 'farewell'"),
            ({"models": [{"provider": "Nope", "model": "x"}]}, "Unknown language model provider 'Nope'"),
            (
                {
                    "metrics": [
                        {
                            "type": "llm_judge",
                            "params": {
                                "criteria": [{"name": "c", "description": "d"}],
                                "judge": {"provider": "Nope", "model": "x"},
                            },
                        }
                    ]
                },
                "Unknown language model provider 'Nope'",
            ),
            (
                {"metrics": [{"type": "llm_judge", "params": {"criteria": [{"name": "c", "description": "d"}]}}]},
                "needs a judge model",
            ),
            ({"variants": [{"name": "v2", "system_prompt_file": "v2.txt"}]}, "no prompt file v2.txt"),
            ({"metrics": [{"type": "no_such_metric"}]}, "Unknown metric 'no_such_metric'"),
            ({"metrics": [{"type": "mock_called", "name": "cost_usd", "params": {"method": "greet"}}]}, "reserved"),
            ({"metrics": [{"type": "mock_called", "name": "pass_rate", "params": {"method": "greet"}}]}, "reserved"),
            (
                {"metrics": [{"type": "mock_called", "name": "judge.tone", "params": {"method": "greet"}}]},
                "may not contain",
            ),
            ({"metrics": [{"type": "mock_called", "name": "tag:x", "params": {"method": "greet"}}]}, "may not contain"),
            (
                {
                    "metrics": [
                        {
                            "type": "llm_classify",
                            "aggregate": "mean",
                            "params": {
                                "question": "q",
                                "labels": ["a", "b"],
                                "judge": {"provider": "OpenAI", "model": "m"},
                            },
                        }
                    ]
                },
                "only aggregate is distribution",
            ),
            (
                {
                    "cases": [
                        {
                            "id": "ada",
                            "input": {"name": "Ada"},
                            "metrics": [{"type": "mock_called", "params": {"method": "greet"}, "aggregate": "max"}],
                        }
                    ]
                },
                "must keep the value type and aggregate",
            ),
            (
                {"integrations": [{"class": GREETER, "config": {"behaviour": {"wave": {"returns": "Hi"}}}}]},
                "no method named wave",
            ),
            ({"cases": [{"id": "ada", "input": {"nickname": "Ada"}}]}, "Case 'ada': invalid input"),
            (
                {"metrics": [{"type": "mock_called", "params": {"method": "greet"}, "aggregate": "distribution"}]},
                "only for label metrics",
            ),
        ],
    )
    def test_fails_early_on_a_suite_the_host_cannot_run(self, tmp_path, changes, message):
        with pytest.raises(EvalSuiteError, match=message):
            _load(tmp_path, **changes)


class TestJudgeModels:
    def test_lists_the_suites_judge_and_each_metrics_own_judge_once(self, tmp_path):
        judge = {"provider": "OpenAI", "model": "gpt-4.1"}
        criteria = [{"name": "c", "description": "d"}]
        metrics = [
            {"type": "llm_judge", "name": "a", "params": {"criteria": criteria}},
            {
                "type": "llm_judge",
                "name": "b",
                "params": {"criteria": criteria, "judge": {"provider": "OpenAI", "model": "gpt-5"}},
            },
            {"type": "llm_judge", "name": "c", "params": {"criteria": criteria, "judge": judge}},
        ]

        loaded = _load(tmp_path, judge=judge, metrics=metrics)

        assert [t.model for t in judge_models_used_by_metrics(loaded)] == ["gpt-4.1", "gpt-5"]

    def test_a_suite_judge_no_llm_metric_relies_on_is_left_out(self, tmp_path):
        loaded = _load(tmp_path, judge={"provider": "OpenAI", "model": "gpt-4.1"})

        assert judge_models_used_by_metrics(loaded) == []
