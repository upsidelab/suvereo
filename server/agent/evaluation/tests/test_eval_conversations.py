import pytest
from django.core.files.base import ContentFile
from django.db.models import ProtectedError
from model_bakery import baker

from agent.evaluation.eval_conversations import EvalConversations
from agent.evaluation.eval_user import EvalUser
from agent.models import Agent, AgenticExecution, Conversation, Message
from agent.models.conversation import ConversationFile

pytestmark = pytest.mark.django_db


class TestEvalConversations:
    def test_a_protected_conversation_is_left_whole(self, temp_media_root):
        conversation = EvalConversations.create(baker.make(Agent, config={}), EvalUser.get())
        baker.make(Message, conversation=conversation)
        stored = ConversationFile.objects.create(conversation=conversation, file=ContentFile(b"x", name="order.pdf"))
        baker.make(AgenticExecution, conversation=conversation, agent=conversation.agent)

        with pytest.raises(ProtectedError):
            EvalConversations.delete(Conversation.objects.filter(pk=conversation.pk))

        assert Message.objects.filter(conversation=conversation).exists()
        assert ConversationFile.objects.filter(pk=stored.pk).exists()
        assert stored.file.storage.exists(stored.file.name)
