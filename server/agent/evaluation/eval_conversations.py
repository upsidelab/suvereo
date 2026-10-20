import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Max, QuerySet
from django.utils import timezone

from account.models import User
from agent.models import Agent, Conversation, Message
from agent.models.conversation import ConversationFile

logger = logging.getLogger(__name__)

SUMMARY = "Evaluation run"
KEPT_SUMMARY = "Evaluation run (kept)"
ABANDONED_AFTER = timedelta(hours=6)


class EvalConversations:
    """Creates the conversations evaluation runs happen in, and deletes them with their messages and files."""

    @staticmethod
    def create(agent: Agent, user: User) -> Conversation:
        return Conversation.objects.create(user=user, data_set=agent.dataset, agent=agent, summary=SUMMARY)

    @staticmethod
    def keep(conversations: QuerySet[Conversation]) -> None:
        """Mark conversations as kept for inspection, so purge_abandoned leaves them."""
        conversations.update(summary=KEPT_SUMMARY)

    @staticmethod
    def last_activity(conversations: QuerySet[Conversation]):
        """When the latest of these conversations started or got a message, or None for no conversations."""
        latest = conversations.aggregate(started=Max("started_at"), messaged=Max("messages__created_at"))
        times = [t for t in latest.values() if t is not None]
        return max(times) if times else None

    @classmethod
    def purge_abandoned(cls, user: User) -> int:
        """Delete evaluation conversations left on real DataSets by runs that died, per DataSet whose evaluation
        conversations have seen no activity for ABANDONED_AFTER; kept ones are spared. Returns how many were deleted.
        """
        candidates = Conversation.objects.filter(user=user, summary=SUMMARY)
        deleted = 0
        for data_set_id in candidates.values_list("data_set_id", flat=True).distinct():
            conversations = candidates.filter(data_set_id=data_set_id)
            latest = cls.last_activity(conversations)
            if latest is not None and timezone.now() - latest <= ABANDONED_AFTER:
                continue
            count = conversations.count()
            try:
                cls.delete(conversations)
            except Exception:
                logger.warning(
                    "Could not purge abandoned evaluation conversations on DataSet %s", data_set_id, exc_info=True
                )
                continue
            deleted += count
        return deleted

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
