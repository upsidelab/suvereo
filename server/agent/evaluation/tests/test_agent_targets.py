from unittest.mock import MagicMock, patch

import pytest
from model_bakery import baker

from agent.core.registries.agents.agent_registry import AgentRegistry
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

    def test_keeps_conversations_when_asked(self):
        agent = baker.make(Agent, config={})

        with ExistingAgentTarget(agent.pk, EvalUser.get(), keep_conversations=True) as target:
            conversation = target.new_conversation()

        assert Conversation.objects.filter(pk=conversation.pk).exists()

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
        with SandboxAgentTarget(
            "quickstart", "order-intake", {}, [], EvalUser.get(), keep_conversations=True
        ) as target:
            conversation = target.new_conversation()

        with patch("agent.evaluation.sandbox.STALE_AFTER_SECONDS", -1):
            EvalSandbox.purge_stale()

        assert Conversation.objects.filter(pk=conversation.pk).exists()
        assert DataSet.objects.get(pk=target.agent.dataset_id).name.startswith(KEPT_PREFIX)
