from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework import status

from account.authorization import PERMISSIONS
from account.tests.helpers import grant
from agent.conversation.tasks import SaveMessageOnFailureTask, respond_to_user_message_task
from agent.conversation.turn_lock import ConversationTurnLock

pytestmark = pytest.mark.django_db


class TestConversationTurnLock:
    def test_a_held_lock_cannot_be_taken_again(self):
        ConversationTurnLock(1).acquire()

        assert ConversationTurnLock(1).acquire() is False

    def test_a_released_lock_can_be_taken_again(self):
        lock = ConversationTurnLock(1)
        lock.acquire()
        lock.release()

        assert lock.acquire() is True

    def test_each_conversation_has_its_own_lock(self):
        ConversationTurnLock(1).acquire()

        assert ConversationTurnLock(2).acquire() is True


class TestAskingWhileAnswering:
    @pytest.fixture
    def post(self, api_client, user, conversation):
        grant(user, PERMISSIONS.CONVERSATION.CONVERSE)
        url = reverse("conversation-details", kwargs={"conversation_id": conversation.id})
        payload = {"data_set_id": conversation.data_set.id, "question_message": "Hello?", "streaming": False}
        with patch("agent.conversation.views.LanguageModelRegistry.provider_for_dataset") as provider:
            provider.return_value = type("obj", (), {"STREAMING_AVAILABLE": False})
            yield lambda: api_client.post(url, payload, format="json")

    @pytest.fixture
    def apply_async(self):
        with patch("agent.conversation.views.respond_to_user_message_task.apply_async") as apply_async:
            apply_async.return_value = type("obj", (), {"id": "fake-task-id"})
            yield apply_async

    def test_a_message_sent_before_the_previous_one_is_answered_is_rejected(self, post, apply_async):
        post()

        response = post()

        assert response.status_code == status.HTTP_409_CONFLICT
        apply_async.assert_called_once()

    def test_a_message_sent_after_the_previous_one_is_answered_is_accepted(self, post, apply_async, conversation):
        post()
        ConversationTurnLock(conversation.id).release()

        assert post().status_code == status.HTTP_202_ACCEPTED

    def test_the_conversation_is_freed_when_the_message_cannot_be_queued(self, post, apply_async, conversation):
        apply_async.side_effect = RuntimeError("broker down")

        with pytest.raises(RuntimeError):
            post()

        assert ConversationTurnLock(conversation.id).acquire() is True


class TestAnsweringFreesTheConversation:
    def test_after_an_answer(self, conversation):
        ConversationTurnLock(conversation.id).acquire()

        with (
            patch("agent.conversation.tasks.ConversationManager") as manager,
            patch("agent.conversation.tasks.compact_conversation_task"),
        ):
            manager.return_value.respond_to_user_message.return_value = MagicMock(id=1)
            respond_to_user_message_task.apply(
                kwargs={
                    "conversation_id": conversation.id,
                    "data_set_id": conversation.data_set.id,
                    "user_id": conversation.user.id,
                    "message": "Hello?",
                    "streaming": False,
                }
            )

        assert ConversationTurnLock(conversation.id).acquire() is True

    def test_after_a_failure_even_if_saving_the_failure_fails(self, conversation):
        ConversationTurnLock(conversation.id).acquire()

        with patch.object(SaveMessageOnFailureTask, "_save_failed_turn", side_effect=RuntimeError("db down")):
            with pytest.raises(RuntimeError):
                SaveMessageOnFailureTask().on_failure(
                    RuntimeError("llm down"), "task-id", (), {"conversation_id": conversation.id}, None
                )

        assert ConversationTurnLock(conversation.id).acquire() is True
