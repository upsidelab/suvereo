import pytest
from model_bakery import baker

from agent.evaluation.repositories import EvalAgentRepository, EvalConversationRepository, EvalDataSetRepository
from agent.models import Agent, Conversation
from catalog.models import DataSet

pytestmark = pytest.mark.django_db


class TestEvalRepositories:
    def test_get_by_id_finds_a_temporary_conversation(self):
        conversation = baker.make(Conversation, is_temporary=True)
        repository = EvalConversationRepository(Conversation)

        assert repository.get_by_id(conversation.pk) == conversation
        assert repository.get_data_set_id(conversation.pk) == conversation.data_set.id

    def test_get_by_id_finds_a_temporary_data_set(self):
        data_set = baker.make(DataSet, is_temporary=True)

        assert EvalDataSetRepository(DataSet).get_by_id(data_set.pk) == data_set

    def test_get_by_id_finds_an_agent_on_a_temporary_data_set(self):
        agent = baker.make(Agent, config={"x": 1}, dataset=baker.make(DataSet, is_temporary=True))
        repository = EvalAgentRepository(Agent)

        assert repository.get_by_id(agent.pk) == agent
        assert repository.get_agent_configuration_by_id(agent.pk) == {"x": 1}

    def test_filter_and_delete_see_the_same_temporary_rows_as_get_by_id(self):
        conversation = baker.make(Conversation, is_temporary=True)
        repository = EvalConversationRepository(Conversation)

        assert list(repository.filter(pk=conversation.pk)) == [conversation]
        assert repository.delete(conversation.pk) is True
        assert repository.get_by_id(conversation.pk) is None
