from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from model_bakery import baker

from agent.evaluation.abandoned_runs import AbandonedRuns
from agent.evaluation.eval_user import EvalUser
from agent.models import Agent, Conversation
from catalog.models import DataSet
from catalog.services import DataSetDeletionService

pytestmark = pytest.mark.django_db

SEVEN_HOURS_AGO = timedelta(hours=7)


def _sandbox(age=SEVEN_HOURS_AGO, name="sandbox"):
    data_set = baker.make(DataSet, name=name, is_temporary=True)
    agent = baker.make(Agent, dataset=data_set, config={})
    Agent.all_objects.filter(pk=agent.pk).update(created_at=timezone.now() - age)
    return data_set, agent


def _conversation(agent, data_set, age=SEVEN_HOURS_AGO, is_temporary=True, user=None):
    user = user or EvalUser.get()
    conversation = baker.make(Conversation, agent=agent, data_set=data_set, is_temporary=is_temporary, user=user)
    Conversation.all_objects.filter(pk=conversation.pk).update(started_at=timezone.now() - age)
    return conversation


class TestPurgeSandboxes:
    def test_removes_only_abandoned_sandboxes(self):
        fresh, _ = _sandbox(age=timedelta(minutes=5))
        stale, _ = _sandbox()
        regular = baker.make(DataSet, name="Shop")

        assert AbandonedRuns.purge_sandboxes() == 1

        assert set(DataSet.all_objects.values_list("pk", flat=True)) == {fresh.pk, regular.pk}

    def test_an_old_sandbox_still_starting_conversations_is_kept(self):
        data_set, agent = _sandbox()
        _conversation(agent, data_set, age=timedelta(minutes=5))

        assert AbandonedRuns.purge_sandboxes() == 0
        assert DataSet.all_objects.filter(pk=data_set.pk).exists()

    def test_a_sandbox_that_cannot_be_deleted_does_not_block_the_rest(self):
        (stuck, _), (stale, _) = _sandbox(name="stuck"), _sandbox(name="stale")
        delete = DataSetDeletionService.delete

        def delete_unless_stuck(data_set):
            if data_set == stuck:
                raise RuntimeError("protected")
            delete(data_set)

        with patch.object(DataSetDeletionService, "delete", delete_unless_stuck):
            assert AbandonedRuns.purge_sandboxes() == 1

        assert DataSet.all_objects.filter(pk=stuck.pk).exists()
        assert not DataSet.all_objects.filter(pk=stale.pk).exists()


class TestPurgeConversations:
    def test_removes_abandoned_temporary_conversations_on_regular_data_sets(self):
        agent = baker.make(Agent, config={})
        abandoned = _conversation(agent, agent.dataset)
        regular = _conversation(agent, agent.dataset, is_temporary=False)

        assert AbandonedRuns.purge_conversations() == 1

        assert set(Conversation.all_objects.values_list("pk", flat=True)) == {regular.pk}
        assert not Conversation.all_objects.filter(pk=abandoned.pk).exists()

    def test_recent_temporary_conversations_are_kept(self):
        agent = baker.make(Agent, config={})
        live = _conversation(agent, agent.dataset, age=timedelta(minutes=5))

        assert AbandonedRuns.purge_conversations() == 0
        assert Conversation.all_objects.filter(pk=live.pk).exists()

    def test_temporary_conversations_of_other_users_are_left_alone(self):
        agent = baker.make(Agent, config={})
        someone_elses = _conversation(agent, agent.dataset, user=baker.make("account.User"))

        assert AbandonedRuns.purge_conversations() == 0
        assert Conversation.all_objects.filter(pk=someone_elses.pk).exists()
