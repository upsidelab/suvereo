from django.db import transaction
from django.db.models import QuerySet

from agent.models import AgenticExecution, Conversation, Message
from agent.models.conversation import ConversationFile


class ConversationDeletionService:
    """Deletes conversations with everything that points at them, and their stored files once that commits."""

    @staticmethod
    def delete(conversations: QuerySet[Conversation]) -> None:
        ids = list(conversations.values_list("id", flat=True))
        files = [f.file for f in ConversationFile.objects.filter(conversation_id__in=ids)]
        with transaction.atomic():
            ConversationFile.objects.filter(conversation_id__in=ids).delete()
            AgenticExecution.objects.filter(conversation_id__in=ids).delete()
            Conversation.all_objects.filter(id__in=ids).update(last_summarized_message=None)
            Message.objects.filter(conversation_id__in=ids).delete()
            Conversation.all_objects.filter(id__in=ids).delete()
            transaction.on_commit(lambda: [file.delete(save=False) for file in files])
