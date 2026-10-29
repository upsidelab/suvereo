from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import QuerySet
from model_bakery import baker

from agent.models import Agent, AgenticExecution, Conversation, Message
from agent.models.conversation import ConversationFile
from agent.services import ConversationDeletionService

pytestmark = pytest.mark.django_db


def _conversation_with_everything():
    agent = baker.make(Agent, config={})
    conversation = baker.make(Conversation, agent=agent, data_set=agent.dataset)
    message = baker.make(Message, conversation=conversation)
    Conversation.objects.filter(pk=conversation.pk).update(last_summarized_message=message)
    stored = ConversationFile.objects.create(conversation=conversation, file=ContentFile(b"x", name="order.pdf"))
    baker.make(AgenticExecution, conversation=conversation, agent=agent)
    return conversation, stored


class TestConversationDeletionService:
    def test_deletes_conversations_with_their_messages_files_and_executions(
        self, temp_media_root, django_capture_on_commit_callbacks
    ):
        conversation, stored = _conversation_with_everything()
        storage, path = stored.file.storage, stored.file.name

        with django_capture_on_commit_callbacks(execute=True):
            ConversationDeletionService.delete(Conversation.objects.filter(pk=conversation.pk))

        assert not Conversation.objects.filter(pk=conversation.pk).exists()
        assert not Message.objects.filter(conversation_id=conversation.pk).exists()
        assert not AgenticExecution.objects.filter(conversation_id=conversation.pk).exists()
        assert not storage.exists(path)

    def test_a_failed_delete_leaves_the_conversation_whole(self, temp_media_root):
        conversation, stored = _conversation_with_everything()

        delete = QuerySet.delete

        def fail_on_conversations(queryset):
            if queryset.model is Conversation:
                raise RuntimeError("protected")
            return delete(queryset)

        with patch.object(QuerySet, "delete", fail_on_conversations):
            with pytest.raises(RuntimeError):
                ConversationDeletionService.delete(Conversation.objects.filter(pk=conversation.pk))

        assert Message.objects.filter(conversation=conversation).exists()
        assert ConversationFile.objects.filter(pk=stored.pk).exists()
        assert stored.file.storage.exists(stored.file.name)

    def test_stored_files_stay_when_an_enclosing_transaction_rolls_back(
        self, temp_media_root, django_capture_on_commit_callbacks
    ):
        conversation, stored = _conversation_with_everything()

        with django_capture_on_commit_callbacks(execute=True):
            with pytest.raises(RuntimeError):
                with transaction.atomic():
                    ConversationDeletionService.delete(Conversation.objects.filter(pk=conversation.pk))
                    raise RuntimeError("the data set could not be deleted")

        assert Conversation.objects.filter(pk=conversation.pk).exists()
        assert stored.file.storage.exists(stored.file.name)
