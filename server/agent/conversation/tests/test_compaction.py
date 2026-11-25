from unittest.mock import MagicMock, patch

import pytest
from celery.exceptions import Retry

from agent.conversation.compaction_lock import ConversationCompactionLock
from agent.conversation.tasks import compact_conversation_task, respond_to_user_message_task
from agent.conversation.turn_lock import ConversationTurnLock
from agent.core.registries.agents.agent_registry import AgentRegistry

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def free_locks():
    yield
    for lock in (ConversationCompactionLock(1), ConversationTurnLock(1)):
        lock.release()


class TestConversationCompactionLock:
    def test_a_held_lock_cannot_be_taken_again(self):
        ConversationCompactionLock(1).acquire()

        assert ConversationCompactionLock(1).acquire() is False

    def test_a_released_lock_can_be_taken_again(self):
        lock = ConversationCompactionLock(1)
        lock.acquire()
        lock.release()

        assert lock.acquire() is True

    def test_is_independent_of_the_turn_lock(self):
        ConversationTurnLock(1).acquire()

        assert ConversationCompactionLock(1).acquire() is True


class TestRespondingQueuesCompaction:
    @pytest.fixture
    def respond(self, conversation):
        def run():
            return respond_to_user_message_task.apply(
                kwargs={
                    "conversation_id": conversation.id,
                    "data_set_id": conversation.data_set.id,
                    "user_id": conversation.user.id,
                    "message": "Hello?",
                    "streaming": False,
                }
            )

        with patch("agent.conversation.tasks.ConversationManager") as manager:
            manager.return_value.respond_to_user_message.return_value = MagicMock(id=1)
            yield run

    def test_after_an_answer(self, conversation, respond):
        with patch("agent.conversation.tasks.compact_conversation_task") as task:
            respond()

        task.delay.assert_called_once_with(conversation_id=conversation.id)

    def test_a_failure_to_queue_does_not_fail_the_turn(self, respond):
        with patch("agent.conversation.tasks.compact_conversation_task") as task:
            task.delay.side_effect = RuntimeError("broker down")
            result = respond()

        assert result.successful()
        assert result.result["message_id"] == 1


class TestCompactConversationTask:
    @pytest.fixture
    def registry(self):
        with patch("agent.conversation.tasks.AgentRegistry") as registry:
            yield registry.return_value

    def test_compacts_the_conversation(self, conversation, registry):
        compact_conversation_task.apply(kwargs={"conversation_id": conversation.id})

        registry.get_memory_compactor.return_value.compact_if_needed.assert_called_once()

    def test_does_nothing_when_the_agent_has_no_compactor(self, conversation, registry):
        registry.get_memory_compactor.return_value = None

        result = compact_conversation_task.apply(kwargs={"conversation_id": conversation.id})

        assert result.successful()

    def test_skips_when_another_compaction_is_running(self, conversation, registry):
        ConversationCompactionLock(conversation.id).acquire()

        compact_conversation_task.apply(kwargs={"conversation_id": conversation.id})

        registry.get_memory_compactor.assert_not_called()

    def test_releases_the_lock(self, conversation, registry):
        compact_conversation_task.apply(kwargs={"conversation_id": conversation.id})

        assert ConversationCompactionLock(conversation.id).acquire() is True

    def test_releases_the_lock_when_compaction_fails(self, conversation, registry):
        registry.get_memory_compactor.return_value.compact_if_needed.side_effect = RuntimeError("llm down")

        compact_conversation_task.apply(kwargs={"conversation_id": conversation.id})

        assert ConversationCompactionLock(conversation.id).acquire() is True

    def test_retries_a_failed_compaction(self, conversation, registry):
        failure = RuntimeError("llm down")
        registry.get_memory_compactor.return_value.compact_if_needed.side_effect = failure

        with patch.object(compact_conversation_task, "retry", side_effect=Retry()) as retry:
            compact_conversation_task.apply(kwargs={"conversation_id": conversation.id})

        retry.assert_called_once_with(exc=failure, countdown=5)

    def test_a_failure_after_the_last_retry_is_only_logged(self, conversation, registry, caplog):
        registry.get_memory_compactor.return_value.compact_if_needed.side_effect = RuntimeError("llm down")

        result = compact_conversation_task.apply(
            kwargs={"conversation_id": conversation.id}, retries=compact_conversation_task.max_retries
        )

        assert result.successful()
        assert "Compaction of conversation" in caplog.text


class TestAgentRegistryMemoryCompactor:
    def test_returns_the_compactor_of_the_conversation_agent(self, conversation):
        registry = AgentRegistry()

        with patch.object(registry, "get_conversation_agent") as get_agent:
            compactor = registry.get_memory_compactor(conversation)

        get_agent.assert_called_once_with(conversation, streaming=False)
        assert compactor is get_agent.return_value.memory_compactor
