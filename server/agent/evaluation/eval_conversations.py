from django.db import transaction
from django.db.models import QuerySet

from account.models import User
from agent.models import Agent, Conversation, Message
from agent.models.conversation import ConversationFile


class EvalConversations:
    """Creates the conversations evaluation runs happen in, and deletes them with their messages and files."""

    @staticmethod
    def create(agent: Agent, user: User) -> Conversation:
        return Conversation.objects.create(user=user, data_set=agent.dataset, agent=agent, summary="Evaluation run")

    @staticmethod
    def delete(conversations: QuerySet[Conversation]) -> None:
        """Delete conversations with their messages and files in one transaction, then the stored files."""
        ids = list(conversations.values_list("id", flat=True))
        files = [f.file for f in ConversationFile.objects.filter(conversation_id__in=ids)]
        with transaction.atomic():
            ConversationFile.objects.filter(conversation_id__in=ids).delete()
            Conversation.objects.filter(id__in=ids).update(last_summarized_message=None)
            Message.objects.filter(conversation_id__in=ids).delete()
            Conversation.objects.filter(id__in=ids).delete()
        for file in files:
            file.delete(save=False)
