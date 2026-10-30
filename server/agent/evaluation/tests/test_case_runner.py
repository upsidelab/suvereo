from unittest.mock import patch

import pytest
from model_bakery import baker
from suvereo_common.evaluation.loaded_suite import LoadedSuite
from suvereo_common.evaluation.suite import (
    AgenticExecutionEvalCase,
    ConversationEvalCase,
    EvalSuite,
    ModelTarget,
    PromptVariant,
)

from agent.agentic_execution.registry import AgenticExecutionDefinitionRegistry
from agent.evaluation.eval_user import EvalUser
from agent.evaluation.integrations import EvalIntegrationPluginResolver
from agent.evaluation.model_client import EvalModelClient
from agent.evaluation.pinned_llm import PinnedLLM
from agent.evaluation.pricing_table import PricingTable, TraceCost
from agent.evaluation.runner import CaseRunner, EvalExecutionConversation
from agent.evaluation.targets import ExistingAgentTarget
from agent.models import Agent
from agent.models.conversation import ConversationFile

from .greeter import GreeterMockIntegration, GreetingExecution

pytestmark = pytest.mark.django_db

GREETER = f"{GreeterMockIntegration.__module__}.GreeterMockIntegration"


@pytest.fixture(autouse=True)
def _registered():
    with patch.object(AgenticExecutionDefinitionRegistry, "get_by_key", return_value=GreetingExecution):
        yield


@pytest.fixture
def target():
    agent = baker.make(Agent, config={}, file_upload=True)
    with ExistingAgentTarget(agent.pk, EvalUser.get()) as opened:
        yield opened


def _runner(target, tmp_path, **changes):
    suite = EvalSuite.model_validate(
        {
            "agent": {"id": target.agent.pk},
            "execution_key": "greeting",
            "integrations": [{"class": GREETER, "config": {"behaviour": {"greet": {"returns": "Hello {name}"}}}}],
            "metrics": [
                {
                    "type": "mock_called",
                    "name": "greeted_once",
                    "params": {"method": "greet"},
                    "pass_threshold": {"equals": 1},
                }
            ],
            "cases": [],
            **changes,
        }
    )
    return CaseRunner(LoadedSuite(path=tmp_path / "suite.yaml", suite=suite, cases=[]), target, PricingTable({}))


def _case(**fields):
    return AgenticExecutionEvalCase(id="ada", input={"name": "Ada"}, **fields)


class TestCaseRunner:
    def test_a_run_records_its_trace_and_passes_its_thresholds(self, target, tmp_path):
        result = _runner(target, tmp_path).run(_case())

        assert result.passed
        assert (result.case_id, result.model, result.variant, result.repeat) == ("ada", "", "default", 1)
        assert result.metrics["greeted_once"].value == 1
        assert result.metrics["execution_succeeded"].value is True
        assert result.metrics["judge_cost_usd"].value == 0.0
        assert result.trace.output == {"greeting": "Hello Ada"}
        assert result.trace.scratchpad == {"greet": "Hello Ada"}
        assert [(a.number, a.passed) for a in result.trace.attempts] == [(1, True)]
        assert [c.method for c in result.trace.mock_calls] == ["greet"]

    def test_an_exception_is_recorded_as_the_runs_error(self, target, tmp_path):
        broken = {
            "class": GREETER,
            "config": {"behaviour": {"greet": {"raises": {"error": "ValueError", "message": "down"}}}},
        }

        result = _runner(target, tmp_path).run(_case(integrations=[broken]))

        assert not result.passed
        assert result.trace.error == "ValueError: down"
        assert result.metrics["failure_code"].value == "RUNTIME_ERROR"
        assert result.thresholds["greeted_once"].passed

    def test_a_conversation_case_is_refused_rather_than_run_as_an_execution(self, target, tmp_path):
        case = ConversationEvalCase(id="chat", user_messages=["Hi"])

        result = _runner(target, tmp_path).run(case)

        assert result.trace.error == "TypeError: Case 'chat' is not an execution case; this suite runs executions."
        assert not result.passed

    def test_a_failure_while_setting_up_is_recorded_too(self, target, tmp_path):
        variant = PromptVariant(name="v2", system_prompt_file="missing.txt")

        result = _runner(target, tmp_path).run(_case(), variant=variant)

        assert not result.passed
        assert result.trace.error.startswith("FileNotFoundError")
        assert result.metrics["duration_s"].value is None

    def test_a_conversation_run_that_never_ran_gets_the_conversation_outcome(self, target, tmp_path):
        loaded = _runner(target, tmp_path, kind="conversation", execution_key=None).loaded

        case = ConversationEvalCase(id="c", simulated_user={"goal": "Get a greeting"})

        result = CaseRunner.errored_result(loaded, case, None, None, 1, "No sandbox")

        assert not result.passed
        assert result.metrics["conversation_completed"].value is False
        assert result.metrics["goal_reached"].details == {"reasoning": "the conversation never started"}
        assert result.metrics["user_cost_usd"].value == 0.0
        assert "attempts" not in result.metrics

    def test_a_judge_no_metric_asks_is_never_built(self, target, tmp_path):
        result = _runner(target, tmp_path, judge={"provider": "Unknown", "model": "x"}).run(_case())

        assert result.passed
        assert result.metrics["judge_cost_usd"].value == 0.0

    def test_a_metrics_own_judge_is_asked_without_a_suite_judge(self, target, tmp_path):
        judge = {"provider": "OpenAI", "model": "judge-x"}
        metrics = [{"type": "llm_judge", "params": {"criteria": [{"name": "c", "description": "d"}], "judge": judge}}]

        with patch.object(EvalModelClient, "complete", return_value='{"score": 1}') as complete:
            result = _runner(target, tmp_path, metrics=metrics).run(_case())

        assert result.metrics["llm_judge"].value == 1.0
        assert complete.call_args.args[1] == ModelTarget.model_validate(judge)

    def test_a_metric_that_cannot_be_built_fails_the_run_even_without_a_threshold(self, target, tmp_path):
        metrics = [{"type": "no_such_metric", "name": "broken"}]

        result = _runner(target, tmp_path, metrics=metrics).run(_case())

        assert not result.passed and result.thresholds["broken"].passed is False

    def test_a_metric_that_cannot_be_built_fails_its_threshold_not_the_runner(self, target, tmp_path):
        metrics = [{"type": "no_such_metric", "name": "broken", "pass_threshold": {"min": 1}}]

        result = _runner(target, tmp_path, metrics=metrics).run(_case())

        assert not result.passed
        assert result.metrics["broken"].value is None
        assert "no_such_metric" in result.metrics["broken"].details["error"]

    def test_an_unpriced_judge_model_is_named(self, target, tmp_path):
        unpriced = TraceCost(usd=None, unpriced_models=["judge-x"])

        judged = [{"type": "llm_judge", "params": {"criteria": [{"name": "c", "description": "d"}]}}]

        with (
            patch.object(EvalModelClient, "cost", return_value=unpriced),
            patch.object(EvalModelClient, "complete", return_value='{"score": 1}'),
        ):
            runner = _runner(target, tmp_path, judge={"provider": "OpenAI", "model": "judge-x"}, metrics=judged)
            result = runner.run(_case())

        assert result.metrics["judge_cost_usd"].value is None
        assert result.unpriced_models == ["judge-x"]

    def test_a_failed_optional_threshold_does_not_fail_the_run(self, target, tmp_path):
        metrics = [
            {"type": "mock_called", "params": {"method": "greet"}, "pass_threshold": {"equals": 2}, "required": False}
        ]

        result = _runner(target, tmp_path, metrics=metrics).run(_case())

        assert result.passed
        assert not result.thresholds["mock_called"].passed

    def test_case_files_are_attached_to_the_conversation(self, target, tmp_path, temp_media_root):
        order = tmp_path / "order.txt"
        order.write_text("2 x SKU-1")

        _runner(target, tmp_path).run(_case(files=[order]))

        [attached] = ConversationFile.objects.filter(conversation__agent=target.agent)
        assert (attached.content_type, attached.llm_content) == ("text/plain", "2 x SKU-1")

    def test_the_model_variant_and_trace_reach_the_agent_through_overrides(self, target, tmp_path):
        (tmp_path / "v2.txt").write_text("Be brief.")
        model = ModelTarget(provider="OpenAI", model="gpt-4o", label="4o")
        variant = PromptVariant(name="v2", system_prompt_file="v2.txt", agent_config={"prompt_input": {"tone": "dry"}})

        init = EvalExecutionConversation.__init__
        with patch.object(EvalExecutionConversation, "__init__", autospec=True, side_effect=init) as spy:
            result = _runner(target, tmp_path).run(_case(), model, variant, repeat=2)

        overrides = spy.call_args.args[3]
        assert overrides.llm_class is PinnedLLM.for_model("OpenAI", "gpt-4o")
        assert overrides.system_prompt == "Be brief."
        assert overrides.agent_config_patch == {"prompt_input": {"tone": "dry"}}
        assert overrides.integration_plugin_resolver is EvalIntegrationPluginResolver
        assert (result.model, result.variant, result.repeat) == ("4o", "v2", 2)
