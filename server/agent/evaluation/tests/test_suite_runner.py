from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from enthusiast_common.evaluation.errors import EvalSuiteError
from enthusiast_common.evaluation.loaded_suite import LoadedSuite
from enthusiast_common.evaluation.metrics import MetricResult
from enthusiast_common.evaluation.suite import EvalCase, EvalSuite
from enthusiast_common.evaluation.trace import ExecutionTrace
from model_bakery import baker

from agent.agentic_execution.registry import AgenticExecutionDefinitionRegistry
from agent.core.registries.agents.agent_registry import AgentRegistry
from agent.evaluation.runner import CaseRunner, RunResult, SuiteRunner, SuiteRunOptions
from agent.evaluation.sandbox import EvalSandbox
from agent.models import Agent
from agent.services import AgentPreconfigurationService

from .greeter import GreeterMockIntegration, GreetingExecution

GREETER = f"{GreeterMockIntegration.__module__}.GreeterMockIntegration"
CASES = [EvalCase(id="ada", input={"name": "Ada"}), EvalCase(id="bob", input={"name": "Bob"})]


@pytest.fixture(autouse=True)
def _registered():
    with (
        patch.object(AgenticExecutionDefinitionRegistry, "get_by_key", return_value=GreetingExecution),
        patch.object(AgentRegistry, "get_agent_class_by_type", return_value=MagicMock()),
        patch.object(AgentPreconfigurationService, "default_agent_configuration", return_value={"tools": []}),
    ):
        yield


def _loaded(tmp_path, agent, cases=CASES, **changes):
    suite = EvalSuite.model_validate(
        {
            "agent": {"id": agent.pk} if agent else {"type": "greeter-agent"},
            "execution_key": "greeting",
            "integrations": [{"class": GREETER, "config": {"behaviour": {"greet": {"returns": "Hello {name}"}}}}],
            "metrics": [{"type": "mock_called", "params": {"method": "greet"}, "gate": {"equals": 1}}],
            "cases": [],
            **changes,
        }
    )
    return LoadedSuite(path=tmp_path / "suite.yaml", suite=suite, cases=cases)


def _costing(usd, unpriced=()):
    def run(case, model=None, variant=None, repeat=1):
        metrics = {"cost_usd": MetricResult(value=usd), "judge_cost_usd": MetricResult(value=0.0)}
        return RunResult(
            unpriced_models=list(unpriced),
            case_id=case.id,
            model="",
            variant="default",
            repeat=repeat,
            passed=True,
            metrics=metrics,
            gates={},
            trace=ExecutionTrace(),
        )

    return run


@pytest.mark.django_db
class TestSuiteRunner:
    def test_runs_every_model_variant_case_and_repeat(self, tmp_path):
        loaded = _loaded(
            tmp_path,
            baker.make(Agent, config={}),
            models=[{"provider": "OpenAI", "model": "a"}, {"provider": "OpenAI", "model": "b"}],
            variants=[{"name": "warm", "agent_config": {"tone": "warm"}}],
            repeats=2,
        )

        result = SuiteRunner(loaded).run()

        assert result.planned_runs == len(result.runs) == 16
        assert all(run.passed for run in result.runs)
        assert {(r.model, r.variant, r.case_id, r.repeat) for r in result.runs} == {
            (m, v, c, n) for m in "ab" for v in ("default", "warm") for c in ("ada", "bob") for n in (1, 2)
        }

    def test_stops_starting_runs_once_the_budget_is_spent(self, tmp_path):
        loaded = _loaded(tmp_path, baker.make(Agent, config={}), repeats=3)

        with patch.object(CaseRunner, "run", side_effect=_costing(0.4)):
            result = SuiteRunner(loaded, SuiteRunOptions(budget_usd=1.0)).run()

        assert (len(result.runs), result.planned_runs, result.budget_exceeded) == (3, 6, True)
        assert result.spent_usd == pytest.approx(1.2)

    def test_a_budget_with_an_unpriced_model_is_refused(self, tmp_path):
        loaded = _loaded(tmp_path, baker.make(Agent, config={}), models=[{"provider": "OpenAI", "model": "gpt-new"}])

        with pytest.raises(EvalSuiteError, match="gpt-new has no price"):
            SuiteRunner(loaded, SuiteRunOptions(budget_usd=1.0)).run()

    def test_an_unpriced_run_stops_a_budgeted_suite(self, tmp_path):
        loaded = _loaded(tmp_path, baker.make(Agent, config={}), repeats=3)

        with patch.object(CaseRunner, "run", side_effect=_costing(None, unpriced=["tool-model"])):
            result = SuiteRunner(loaded, SuiteRunOptions(budget_usd=1.0)).run()

        assert (len(result.runs), result.budget_exceeded, result.unpriced_models) == (1, True, ["tool-model"])

    def test_a_sandbox_that_cannot_be_set_up_errors_only_its_own_cases(self, tmp_path):
        override = {"class": GREETER, "config": {"data": {"greeting": "Hi"}}}
        cases = [*CASES, EvalCase(id="cy", input={"name": "Cy"}, integrations=[override])]
        create = EvalSandbox.create

        def create_unless_overridden(suite_name, agent_type, agent_config, integrations):
            if integrations[0].config.data:
                raise RuntimeError("fixture unreadable")
            return create(suite_name, agent_type, agent_config, integrations)

        with patch.object(EvalSandbox, "create", side_effect=create_unless_overridden):
            result = SuiteRunner(_loaded(tmp_path, None, cases=cases)).run()

        by_case = {r.case_id: r for r in result.runs}
        assert by_case["ada"].passed and by_case["bob"].passed
        assert not by_case["cy"].passed
        assert "case(s) cy failed: RuntimeError: fixture unreadable" in by_case["cy"].trace.error
        assert by_case["cy"].metrics["failure_code"].value == "RUNTIME_ERROR"

    def test_a_case_overriding_integration_data_gets_its_own_sandbox(self, tmp_path):
        override = {"class": GREETER, "config": {"data": {"greeting": "Hi"}}}
        cases = [*CASES, EvalCase(id="cy", input={"name": "Cy"}, integrations=[override])]

        with patch.object(EvalSandbox, "create", wraps=EvalSandbox.create) as create:
            result = SuiteRunner(_loaded(tmp_path, None, cases=cases)).run()

        assert create.call_count == 2
        assert [i.config.data for i in create.call_args_list[1].args[3]] == [{"greeting": "Hi"}]
        assert sorted(r.case_id for r in result.runs) == ["ada", "bob", "cy"]

    def test_files_go_to_a_temporary_media_root(self, tmp_path):
        roots = []

        def run(case, *args):
            roots.append(settings.MEDIA_ROOT)
            return _costing(0.0)(case, *args)

        with patch.object(CaseRunner, "run", side_effect=run):
            SuiteRunner(_loaded(tmp_path, baker.make(Agent, config={}))).run()

        assert roots[0] != settings.MEDIA_ROOT and "eval-media-" in roots[0]


@pytest.mark.django_db(transaction=True)
def test_parallel_runs_each_get_their_own_trace(tmp_path):
    loaded = _loaded(tmp_path, baker.make(Agent, config={}), repeats=3)

    result = SuiteRunner(loaded, SuiteRunOptions(parallel=4)).run()

    assert len(result.runs) == 6
    assert all(run.passed and len(run.trace.mock_calls) == 1 for run in result.runs)
