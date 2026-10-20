from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from model_bakery import baker

from agent.core.registries.agents.agent_registry import AgentRegistry
from agent.evaluation.eval_conversations import KEPT_SUMMARY, EvalConversations
from agent.evaluation.eval_user import EvalUser
from agent.evaluation.sandbox import KEPT_PREFIX, NAME_PREFIX, EvalSandbox
from agent.evaluation.targets import ExistingAgentTarget, SandboxAgentTarget
from agent.models import Agent, Conversation
from agent.services import AgentPreconfigurationService
from catalog.integrations.resolver import IntegrationPluginResolver
from catalog.models import DataSet

pytestmark = pytest.mark.django_db


class TestExistingAgentTarget:
    def test_hands_out_conversations_and_deletes_them_on_close(self):
        agent = baker.make(Agent, config={})
        target = ExistingAgentTarget(agent.pk, EvalUser.get())

        with target:
            conversation = target.new_conversation()
            assert (target.agent, conversation.agent) == (agent, agent)

        assert not Conversation.objects.filter(pk=conversation.pk).exists()
        assert Agent.objects.filter(pk=agent.pk).exists()

    def test_keeps_conversations_when_asked_and_marks_them_kept(self):
        agent = baker.make(Agent, config={})

        with ExistingAgentTarget(agent.pk, EvalUser.get(), keep_run_data=True) as target:
            conversation = target.new_conversation()

        assert Conversation.objects.get(pk=conversation.pk).summary == KEPT_SUMMARY

    def test_a_cleanup_failure_is_logged_and_never_hides_the_runs_error(self):
        agent = baker.make(Agent, config={})

        with patch.object(EvalConversations, "delete", side_effect=RuntimeError("protected")):
            with pytest.raises(ValueError, match="the run failed"):
                with ExistingAgentTarget(agent.pk, EvalUser.get()) as target:
                    target.new_conversation()
                    raise ValueError("the run failed")

        assert target._conversation_ids == []

    def test_opening_purges_conversations_abandoned_on_real_data_sets(self):
        agent = baker.make(Agent, config={})
        user = EvalUser.get()
        abandoned, kept = EvalConversations.create(agent, user), EvalConversations.create(agent, user)
        EvalConversations.keep(Conversation.objects.filter(pk=kept.pk))
        Conversation.objects.filter(pk__in=[abandoned.pk, kept.pk]).update(
            started_at=timezone.now() - timedelta(hours=7)
        )
        someone_elses = baker.make(Conversation, agent=agent, data_set=agent.dataset, summary="Evaluation run")

        with ExistingAgentTarget(agent.pk, user):
            pass

        assert set(Conversation.objects.values_list("pk", flat=True)) == {kept.pk, someone_elses.pk}

    def test_recent_evaluation_conversations_are_not_purged(self):
        agent = baker.make(Agent, config={})
        user = EvalUser.get()
        live = EvalConversations.create(agent, user)

        assert EvalConversations.purge_abandoned(user) == 0
        assert Conversation.objects.filter(pk=live.pk).exists()

    @pytest.mark.parametrize("allowed, resolver", [(False, None), (True, IntegrationPluginResolver)])
    def test_real_integrations_only_when_allowed(self, allowed, resolver):
        assert ExistingAgentTarget(1, EvalUser.get(), allow_real_integrations=allowed).real_resolver is resolver


class TestSandboxAgentTarget:
    @pytest.fixture(autouse=True)
    def _agent_type(self):
        with (
            patch.object(AgentRegistry, "get_agent_class_by_type", return_value=MagicMock()),
            patch.object(AgentPreconfigurationService, "default_agent_configuration", return_value={"tools": []}),
        ):
            yield

    def test_builds_a_sandbox_and_removes_it_on_close(self):
        target = SandboxAgentTarget("quickstart", "order-intake", {}, [], EvalUser.get())

        with target:
            target.new_conversation()
            assert target.agent.dataset.name.startswith(NAME_PREFIX)
            assert target.real_resolver is None

        assert not DataSet.objects.filter(name__startswith=NAME_PREFIX).exists()

    def test_keeping_conversations_moves_the_sandbox_out_of_the_purges_reach(self):
        with SandboxAgentTarget("quickstart", "order-intake", {}, [], EvalUser.get(), keep_run_data=True) as target:
            conversation = target.new_conversation()

        with patch("agent.evaluation.sandbox.ABANDONED_AFTER", timedelta(seconds=-1)):
            EvalSandbox.purge_abandoned()

        assert Conversation.objects.filter(pk=conversation.pk).exists()
        assert DataSet.objects.get(pk=target.agent.dataset_id).name.startswith(KEPT_PREFIX)
