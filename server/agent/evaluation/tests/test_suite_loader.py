from unittest.mock import patch

import pytest
import yaml
from enthusiast_common.evaluation.errors import EvalSuiteError

from agent.agentic_execution.registry import AgenticExecutionDefinitionRegistry
from agent.core.registries.agents.agent_registry import AgentNotFoundError, AgentRegistry
from agent.core.registries.language_models import LanguageModelRegistry
from agent.evaluation.judge_models_used_by_metrics import judge_models_used_by_metrics
from agent.evaluation.suite_loader import SuiteLoader

from .greeter import GreeterMockIntegration, GreetingExecution

pytestmark = pytest.mark.django_db

GREETER = f"{GreeterMockIntegration.__module__}.GreeterMockIntegration"
CHATTER = "agent.evaluation.tests.chatter"


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

        assert (loaded.suite.kind, loaded.suite.execution_key) == ("execution", "greeting")
        assert [case.id for case in loaded.cases] == ["ada"]

    def test_an_agent_type_without_an_execution_is_run_as_a_conversation(self, tmp_path):
        with patch.object(AgenticExecutionDefinitionRegistry, "get_all", return_value=[]):
            loaded = _load(tmp_path, cases=[{"id": "chat", "user_messages": ["Hi", "Bye"]}])

        assert (loaded.suite.kind, loaded.suite.execution_key) == ("conversation", None)

    def test_an_execution_key_makes_the_suite_an_execution_so_a_wrong_key_is_named(self, tmp_path):
        with patch.object(AgenticExecutionDefinitionRegistry, "get_all", return_value=[]):
            with pytest.raises(EvalSuiteError, match="has no execution 'greeting'"):
                _load(tmp_path, execution_key="greeting")

    def test_any_agent_can_be_run_as_a_conversation(self, tmp_path):
        user = {"class": f"{CHATTER}.PoliteUser", "params": {"name": "Ada"}}

        loaded = _load(
            tmp_path,
            kind="conversation",
            cases=[{"id": "chat", "user_messages": ["Hi"]}, {"id": "u", "simulated_user": user}],
        )

        assert loaded.suite.kind == "conversation"

    @pytest.mark.parametrize(
        "changes, message",
        [
            ({"cases": [{"id": "chat"}]}, "Case 'chat' is an execution case"),
            ({"cases": [{"id": "chat", "simulated_user": {"goal": "Say hi"}}]}, "'simulated_user' needs 'class'"),
            (
                {"cases": [{"id": "chat", "simulated_user": {"class": "no.such.Simulator"}}]},
                "can't load the user simulator",
            ),
            (
                {"cases": [{"id": "chat", "simulated_user": {"class": f"{CHATTER}.NotASimulator"}}]},
                "is not a BaseUserSimulator",
            ),
            (
                {"metrics": [{"type": "trace_event", "name": "retried", "params": {"event": "retry"}}]},
                "Metric 'retried' \\(trace_event\\) can't measure conversation suites",
            ),
        ],
    )
    def test_a_conversation_suite_fails_early_on_what_it_cannot_run(self, tmp_path, changes, message):
        with pytest.raises(EvalSuiteError, match=message):
            _load(tmp_path, kind="conversation", **{"cases": [{"id": "chat", "user_messages": ["Hi"]}], **changes})

    def test_auto_metric_names_are_reserved_only_in_the_kind_that_measures_them(self, tmp_path):
        metrics = [{"type": "mock_called", "name": "turns", "params": {"method": "greet"}}]

        assert _load(tmp_path, metrics=metrics).suite.metrics[0].name == "turns"
        with pytest.raises(EvalSuiteError, match="'turns' is reserved"):
            _load(tmp_path, kind="conversation", metrics=metrics, cases=[{"id": "chat", "user_messages": ["Hi"]}])

    def test_a_conversation_suite_can_check_tool_errors(self, tmp_path):
        metrics = [{"type": "trace_event", "name": "tool_failed", "params": {"event": "tool_error"}}]

        loaded = _load(tmp_path, kind="conversation", metrics=metrics, cases=[{"id": "chat", "user_messages": ["Hi"]}])

        assert loaded.suite.metrics[0].name == "tool_failed"

    @pytest.mark.parametrize(
        "changes, message",
        [
            ({"agent": {"type": "unknown-agent"}, "kind": "execution"}, "has 0 registered executions"),
            ({"agent": {"type": "unknown-agent"}}, "agent type 'unknown-agent' has no registered execution"),
            ({"agent": {"id": 999}}, "no agent with id 999"),
            ({"execution_key": "farewell"}, "no execution 'farewell'"),
            ({"models": [{"provider": "Nope", "model": "x"}]}, "Language model provider 'Nope' is not installed"),
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
                "Language model provider 'Nope' is not installed",
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
            ({"kind": "conversation"}, "Case 'ada' is an execution case, but this is a conversation suite"),
            (
                {"cases": [{"id": "chat", "user_messages": ["Hi"]}]},
                "Case 'chat': 'user_messages' and 'simulated_user' are for conversation suites",
            ),
            ({"kind": "conversation", "execution_key": "greeting"}, "'execution_key' is for execution suites"),
            (
                {
                    "metrics": [
                        {
                            "type": "llm_judge",
                            "name": "quality",
                            "params": {
                                "criteria": [{"name": "kind", "description": "Is kind"}],
                                "include": ["transcript"],
                            },
                        }
                    ]
                },
                "Metric 'quality' \\(llm_judge\\) can't measure execution suites",
            ),
        ],
    )
    def test_fails_early_on_a_suite_the_host_cannot_run(self, tmp_path, changes, message):
        with pytest.raises(EvalSuiteError, match=message):
            _load(tmp_path, **changes)

    def test_a_provider_that_is_not_installed_is_named_with_the_installed_ones(self, tmp_path):
        with pytest.raises(EvalSuiteError) as error:
            _load(tmp_path, models=[{"provider": "Anthropic", "model": "claude-sonnet-4-6"}])

        assert str(error.value) == (
            "Language model provider 'Anthropic' is not installed. Installed: OpenAI. "
            "Install its model plugin and add it to CATALOG_LANGUAGE_MODEL_PROVIDERS."
        )

    def test_a_registered_provider_that_cannot_be_imported_says_to_install_it(self, tmp_path):
        missing = ["enthusiast_model_missing.MissingLanguageModelProvider"]

        with patch.object(LanguageModelRegistry, "_get_plugin_paths", return_value=missing):
            with pytest.raises(EvalSuiteError, match="A provider in CATALOG_LANGUAGE_MODEL_PROVIDERS can't be loaded"):
                _load(tmp_path)


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
