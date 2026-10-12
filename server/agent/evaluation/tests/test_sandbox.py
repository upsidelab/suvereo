import time
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.base import ContentFile
from model_bakery import baker

from agent.core.registries.agents.agent_registry import AgentRegistry
from agent.evaluation.eval_conversations import EvalConversations
from agent.evaluation.eval_user import EvalUser
from agent.evaluation.integrations import IntegrationFixtureSyncer
from agent.evaluation.sandbox import NAME_PREFIX, EvalSandbox
from agent.models import Agent, Conversation, Message
from agent.models.conversation import ConversationFile
from agent.services import AgentPreconfigurationService
from catalog.integrations.registry import IntegrationManagerRegistry
from catalog.models import DataSet, Integration

from .greeter import GreeterMockIntegration

pytestmark = pytest.mark.django_db

DEFAULT_CONFIG = {
    "agent_args": {},
    "prompt_input": {"tone": "casual", "language": "en"},
    "prompt_extension": {},
    "tools": [],
}


@pytest.fixture(autouse=True)
def _agent_type():
    with (
        patch.object(AgentRegistry, "get_agent_class_by_type", return_value=MagicMock()),
        patch.object(AgentPreconfigurationService, "default_agent_configuration", return_value=DEFAULT_CONFIG),
    ):
        yield


def _create(integrations=(), name="order intake quickstart"):
    return EvalSandbox.create(name, "order-intake", {"prompt_input": {"tone": "formal"}}, list(integrations))


class TestEvalSandbox:
    def test_creates_a_data_set_and_an_agent_with_the_default_config_patched(self):
        sandbox = _create()

        assert sandbox.data_set.name.startswith(NAME_PREFIX) and len(sandbox.data_set.name) <= 30
        assert sandbox.agent.dataset == sandbox.data_set
        assert sandbox.agent.config["prompt_input"] == {"tone": "formal", "language": "en"}

    def test_syncs_each_integration_through_its_manager(self):
        manager = MagicMock()
        integration = GreeterMockIntegration()

        with patch.object(IntegrationManagerRegistry, "get_manager_for", return_value=manager):
            sandbox = _create([integration])

        record = Integration.objects.get(dataset=sandbox.data_set)
        assert record.type == "mock_greeter"
        manager.sync.assert_called_once_with(integration, sandbox.data_set.id, record.id)

    def test_a_failed_sync_leaves_nothing_behind(self):
        with patch.object(IntegrationFixtureSyncer, "sync", side_effect=RuntimeError("catalog unreadable")):
            with pytest.raises(RuntimeError):
                _create([GreeterMockIntegration()])

        assert not DataSet.objects.filter(name__startswith=NAME_PREFIX).exists()

    def test_destroy_removes_everything_including_conversations_and_their_files(self, temp_media_root):
        sandbox = _create()
        conversation = EvalConversations.create(sandbox.agent, EvalUser.get())
        baker.make(Message, conversation=conversation)
        stored = ConversationFile.objects.create(conversation=conversation, file=ContentFile(b"x", name="order.pdf"))
        storage, path = stored.file.storage, stored.file.name

        sandbox.destroy()

        assert not DataSet.objects.filter(pk=sandbox.data_set.pk).exists()
        assert not Agent.all_objects.filter(pk=sandbox.agent.pk).exists()
        assert not Conversation.objects.filter(pk=conversation.pk).exists()
        assert not storage.exists(path)

    def test_purge_removes_only_stale_sandboxes(self):
        fresh = _create().data_set
        stale = baker.make(DataSet, name=f"{NAME_PREFIX}{int(time.time()) - 7 * 3600:x}-ab-old")
        unrelated = baker.make(DataSet, name="Shop")

        assert EvalSandbox.purge_stale() == 1

        assert set(DataSet.objects.values_list("pk", flat=True)) >= {fresh.pk, unrelated.pk}
        assert not DataSet.objects.filter(pk=stale.pk).exists()

    def test_a_sandbox_that_cannot_be_purged_does_not_block_the_rest(self):
        names = [f"{NAME_PREFIX}{int(time.time()) - 7 * 3600:x}-{suffix}" for suffix in ("ab-old", "cd-old")]
        stuck, stale = (baker.make(DataSet, name=name) for name in names)
        destroy = EvalSandbox.destroy

        def destroy_unless_stuck(sandbox):
            if sandbox.data_set == stuck:
                raise RuntimeError("protected")
            destroy(sandbox)

        with patch.object(EvalSandbox, "destroy", destroy_unless_stuck):
            assert EvalSandbox.purge_stale() == 1

        assert DataSet.objects.filter(pk=stuck.pk).exists()
        assert not DataSet.objects.filter(pk=stale.pk).exists()
