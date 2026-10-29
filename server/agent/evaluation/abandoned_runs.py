import logging
from datetime import timedelta

from django.db.models import Min
from django.utils import timezone

from agent.evaluation.eval_user import EvalUser
from agent.models import Agent, Conversation
from agent.services import ConversationDeletionService
from catalog.models import DataSet
from catalog.services import DataSetDeletionService

logger = logging.getLogger(__name__)

ABANDONED_AFTER = timedelta(hours=6)


class AbandonedRuns:
    """Deletes what evaluation runs that died left behind: temporary DataSets (sandboxes) and the evaluation user's
    temporary conversations on regular DataSets, once unused for ABANDONED_AFTER. A run still going keeps them alive
    by starting conversations; one that cannot be deleted is logged and skipped."""

    @classmethod
    def purge(cls) -> int:
        """Purge both; returns how many sandboxes and conversations were deleted."""
        return cls.purge_sandboxes() + cls.purge_conversations()

    @classmethod
    def purge_sandboxes(cls) -> int:
        purged = 0
        for data_set in DataSet.all_objects.filter(is_temporary=True):
            created = Agent.all_objects.filter(dataset=data_set).aggregate(created=Min("created_at"))["created"]
            if not cls._is_abandoned(created, Conversation.all_objects.filter(data_set=data_set)):
                continue
            try:
                DataSetDeletionService.delete(data_set)
            except Exception:
                logger.warning("Could not purge abandoned evaluation sandbox %s", data_set.pk, exc_info=True)
                continue
            purged += 1
        return purged

    @classmethod
    def purge_conversations(cls) -> int:
        temporary = Conversation.all_objects.filter(
            is_temporary=True, data_set__is_temporary=False, user=EvalUser.get()
        )
        purged = 0
        for data_set_id in temporary.values_list("data_set_id", flat=True).distinct():
            conversations = temporary.filter(data_set_id=data_set_id)
            if not cls._is_abandoned(None, conversations):
                continue
            count = conversations.count()
            try:
                ConversationDeletionService.delete(conversations)
            except Exception:
                logger.warning("Could not purge abandoned conversations on DataSet %s", data_set_id, exc_info=True)
                continue
            purged += count
        return purged

    @staticmethod
    def _is_abandoned(created, conversations) -> bool:
        latest = max((t for t in (created, conversations.last_activity()) if t is not None), default=None)
        return latest is None or timezone.now() - latest > ABANDONED_AFTER
