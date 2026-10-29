from unittest.mock import patch

import pytest
from enthusiast_common.evaluation.loaded_suite import LoadedSuite
from enthusiast_common.evaluation.suite import ConversationEvalCase, EvalSuite
from model_bakery import baker

from agent.conversation.manager import ConversationManager
from agent.evaluation.eval_user import EvalUser
from agent.evaluation.integrations import EvalIntegrationPluginResolver
from agent.evaluation.model_client import EvalModelClient
from agent.evaluation.pricing_table import PricingTable, TraceCost
from agent.evaluation.runner import CaseRunner
from agent.evaluation.targets import ExistingAgentTarget
from agent.models import Agent

from .chatter import FakeChat
from .greeter import GreeterMockIntegration

pytestmark = pytest.mark.django_db

GREETER = f"{GreeterMockIntegration.__module__}.GreeterMockIntegration"
CHATTER = "agent.evaluation.tests.chatter"


@pytest.fixture
def chat():
    fake = FakeChat()
    with patch.object(ConversationManager, "get_answer", side_effect=fake):
        yield fake


@pytest.fixture
def target():
    with ExistingAgentTarget(baker.make(Agent, config={}).pk, EvalUser.get()) as opened:
        yield opened


def _run(target, tmp_path, case: ConversationEvalCase, **suite_fields):
    suite = EvalSuite.model_validate(
        {
            **suite_fields,
            "agent": {"id": target.agent.pk},
            "kind": "conversation",
            "integrations": [{"class": GREETER, "config": {"behaviour": {"greet": {"returns": "Hello {name}"}}}}],
            "metrics": [
                {"type": "mock_called", "name": "greeted", "params": {"method": "greet"}, "pass_threshold": {"min": 1}}
            ],
            "cases": [],
        }
    )
    loaded = LoadedSuite(path=tmp_path / "suite.yaml", suite=suite, cases=[case])
    return CaseRunner(loaded, target, PricingTable({})).run(case)


class TestConversationRunDriver:
    def test_scripted_turns_are_sent_in_order_and_recorded_with_their_calls(self, chat, target, tmp_path):
        result = _run(target, tmp_path, ConversationEvalCase(id="c", user_messages=["greet Ada", "thanks"]))

        first, second = result.trace.turns
        assert result.passed
        assert [(t.user_message, t.answer) for t in result.trace.turns] == [
            ("greet Ada", "Hello Ada"),
            ("thanks", "You said: thanks"),
        ]
        assert (first.llm_call_run_ids, first.tool_call_run_ids) == (["llm-1"], ["tool-1"])
        assert (second.llm_call_run_ids, second.tool_call_run_ids) == (["llm-2"], [])
        assert all(turn.duration_s is not None for turn in result.trace.turns)
        assert result.trace.output == {"answer": "You said: thanks"}
        assert result.trace.stop_reason == "done"
        assert [c.method for c in result.trace.mock_calls] == ["greet"]

    def test_every_turn_goes_to_the_same_conversation_as_a_chat_with_the_runs_overrides(self, chat, target, tmp_path):
        _run(target, tmp_path, ConversationEvalCase(id="c", user_messages=["Hi", "thanks"]))

        (first, _, kwargs), (second, _, _) = chat.calls
        assert first.pk == second.pk
        assert first.is_temporary
        assert kwargs["streaming"] is False
        assert kwargs["overrides"].integration_plugin_resolver is EvalIntegrationPluginResolver

    def test_the_outcome_metrics_are_the_conversations(self, chat, target, tmp_path):
        result = _run(target, tmp_path, ConversationEvalCase(id="c", user_messages=["greet Ada", "thanks"]))

        assert result.metrics["conversation_completed"].value is True
        assert result.metrics["turns"].value == 2.0
        assert result.metrics["llm_calls"].value == 2.0
        assert "attempts" not in result.metrics
        assert "execution_succeeded" not in result.metrics

    def test_a_turn_that_raises_ends_the_conversation_and_fails_the_run(self, chat, target, tmp_path):
        result = _run(target, tmp_path, ConversationEvalCase(id="c", user_messages=["greet Ada", "boom", "never sent"]))

        assert [t.user_message for t in result.trace.turns] == ["greet Ada", "boom"]
        assert result.trace.turns[1].error == "RuntimeError: model down"
        assert result.trace.error == "RuntimeError: model down"
        assert result.trace.stop_reason == "error"
        assert result.trace.output == {"answer": "Hello Ada"}
        assert result.metrics["conversation_completed"].value is False
        assert not result.passed

    def test_a_json_answer_exposes_its_fields_to_output_metrics(self, chat, target, tmp_path):
        result = _run(target, tmp_path, ConversationEvalCase(id="c", user_messages=["greet Ada", "json"]))

        assert result.trace.output == {"greeting": "Hi", "answer": '{"greeting": "Hi"}'}

    def test_a_custom_simulator_drives_the_conversation_until_it_stops(self, chat, target, tmp_path):
        user = {"class": f"{CHATTER}.PoliteUser", "params": {"name": "Bob"}}

        result = _run(target, tmp_path, ConversationEvalCase(id="c", simulated_user=user))

        assert [t.user_message for t in result.trace.turns] == ["greet Bob", "thanks"]
        assert result.trace.stop_reason == "done"
        assert result.passed

    def test_a_simulator_that_never_stops_is_cut_off_at_max_turns_and_fails(self, chat, target, tmp_path):
        user = {"class": f"{CHATTER}.EndlessUser", "max_turns": 3}

        result = _run(target, tmp_path, ConversationEvalCase(id="c", simulated_user=user))

        assert len(result.trace.turns) == 3
        assert result.trace.stop_reason == "max_turns"
        assert result.metrics["conversation_completed"].value is False

    def test_a_user_that_gives_up_fails_the_run(self, chat, target, tmp_path):
        result = _run(
            target, tmp_path, ConversationEvalCase(id="c", simulated_user={"class": f"{CHATTER}.GivingUpUser"})
        )

        assert len(result.trace.turns) == 1
        assert result.trace.stop_reason == "gave_up"
        assert result.metrics["conversation_end"].value == "gave_up"
        assert result.metrics["conversation_completed"].value is False
        assert not result.passed

    def test_a_simulator_that_fails_keeps_the_turns_and_output_so_far(self, chat, target, tmp_path):
        result = _run(
            target, tmp_path, ConversationEvalCase(id="c", simulated_user={"class": f"{CHATTER}.FailingUser"})
        )

        assert [t.answer for t in result.trace.turns] == ["You said: Hi"]
        assert result.trace.output == {"answer": "You said: Hi"}
        assert result.trace.error == "RuntimeError: simulator broke"
        assert result.trace.stop_reason == "error"
        assert result.metrics["conversation_completed"].value is False


class FakeModels:
    """Stands in for the user model and the judge: the simulated user asks to greet Ada, then says it is done; the
    judge says the goal was reached."""

    def __init__(self):
        self.user_systems: list[str] = []
        self.user_conversations: list[list] = []
        self.models_asked: set[str] = set()

    def __call__(self, client, messages, system=None, model=None):
        self.models_asked.add((model or client.target).model)
        if "Decide from the transcript whether the" in messages[-1].text:
            return '{"reached": true, "reasoning": "Ada was greeted"}'
        self.user_systems.append(system)
        self.user_conversations.append(messages)
        if len(self.user_conversations) == 1:
            return '{"message": "greet Ada", "stop": null}'
        return '{"message": null, "stop": "done"}'


class TestSimulatedUserConversation:
    JUDGE = {"provider": "OpenAI", "model": "gpt-4o-mini"}
    MODELS = {"judge": JUDGE, "user_model": {"provider": "OpenAI", "model": "gpt-4.1-nano"}}
    USER = {"goal": "Get Ada greeted", "facts": {"name": "Ada"}}

    def test_the_user_model_plays_the_user_and_the_judge_decides_the_goal(self, chat, target, tmp_path):
        models = FakeModels()

        with patch.object(EvalModelClient, "chat", autospec=True, side_effect=models):
            result = _run(target, tmp_path, ConversationEvalCase(id="c", simulated_user=self.USER), **self.MODELS)

        assert [t.user_message for t in result.trace.turns] == ["greet Ada"]
        assert result.trace.stop_reason == "done"
        assert "- name: Ada" in models.user_systems[0]
        assert models.user_conversations[1][-1].text == "Hello Ada"
        assert result.metrics["goal_reached"].value is True
        assert result.metrics["user_cost_usd"].value == 0.0
        assert result.passed
        assert models.models_asked == {"gpt-4.1-nano", "gpt-4o-mini"}

    def test_the_user_model_cost_is_its_own_figure_and_counts_toward_the_spend(self, chat, target, tmp_path):
        def cost(client):
            usd = 0.02 if client.target.model == self.JUDGE["model"] else 0.05
            return TraceCost(usd=usd, priced_usd=usd)

        with (
            patch.object(EvalModelClient, "chat", autospec=True, side_effect=FakeModels()),
            patch.object(EvalModelClient, "cost", autospec=True, side_effect=cost),
        ):
            result = _run(
                target,
                tmp_path,
                ConversationEvalCase(id="c", simulated_user=self.USER),
                **self.MODELS,
            )

        assert (result.metrics["user_cost_usd"].value, result.metrics["judge_cost_usd"].value) == (0.05, 0.02)
        assert result.priced_spend_usd == pytest.approx(0.07)
