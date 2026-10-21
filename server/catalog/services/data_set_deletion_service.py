from django.db import transaction

from agent.models import Conversation
from agent.services import ConversationDeletionService
from catalog.models import DataSet


class DataSetDeletionService:
    """Deletes a DataSet with its conversations first, as they protect it from deletion."""

    @staticmethod
    def delete(data_set: DataSet) -> None:
        with transaction.atomic():
            ConversationDeletionService.delete(Conversation.objects.filter(data_set=data_set))
            data_set.delete()
