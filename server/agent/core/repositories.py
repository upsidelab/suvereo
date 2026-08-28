from typing import Any, Optional, Type, TypeVar

from django.db import models
from django.db.models import QuerySet
from enthusiast_common.repositories import (
    BaseAgentRepository,
    BaseConversationRepository,
    BaseDataSetRepository,
    BaseMessageRepository,
    BaseRepository,
    BaseUserRepository,
)
from enthusiast_common.structures import LLMFile

from account.authorization import PERMISSIONS, datasets_with_permission
from account.models import User
from agent.models import Conversation, Message
from agent.models.agent import Agent
from agent.models.conversation import ConversationFile
from catalog.models import DataSet

T = TypeVar("T", bound=models.Model)


class BaseDjangoRepository(BaseRepository[T]):
    def __init__(self, model: Type[T]):
        super(BaseDjangoRepository, self).__init__(model)
        self.model = model

    def get_by_id(self, pk: int) -> Optional[T]:
        try:
            return self.model.objects.get(pk=pk)
        except self.model.DoesNotExist:
            return None

    def list(self) -> list[T]:
        return list(self.model.objects.all())

    def filter(self, **kwargs) -> QuerySet[T]:
        return self.model.objects.filter(**kwargs)

    def create(self, **kwargs) -> T:
        instance = self.model(**kwargs)
        instance.save()
        return instance

    def update(self, pk: int, **kwargs) -> Optional[T]:
        obj = self.get_by_id(pk)
        if obj:
            for key, value in kwargs.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    def delete(self, pk: int) -> bool:
        deleted, _ = self.model.objects.filter(pk=pk).delete()
        return deleted > 0


class DjangoUserRepository(
    BaseDjangoRepository[User],
    BaseUserRepository,
):
    def get_user_dataset(self, user_id: int, data_set_id: int) -> DataSet:
        user = self.model.objects.get(pk=user_id)
        return datasets_with_permission(user, PERMISSIONS.CONVERSATION.CONVERSE).get(pk=data_set_id)


class DjangoMessageRepository(BaseDjangoRepository[Message], BaseMessageRepository[Message]):
    pass


class DjangoConversationRepository(BaseDjangoRepository[Conversation], BaseConversationRepository[Conversation]):
    def get_data_set_id(self, conversation_id: int) -> int:
        return self.get_by_id(pk=conversation_id).data_set.id

    def get_agent_id(self, conversation_id: int) -> int:
        return self.get_by_id(pk=conversation_id).agent.id

    def list_files(self, conversation_id: int) -> list[LLMFile]:
        return [file.get_llm_file_object() for file in self.get_by_id(pk=conversation_id).files.filter(is_hidden=False)]

    def get_file_objects(self, conversation_id: Any, file_ids: list[Any]) -> list[LLMFile]:
        return [
            file.get_llm_file_object()
            for file in ConversationFile.objects.filter(
                conversation_id=conversation_id, id__in=file_ids, is_hidden=False
            ).order_by("created_at")
        ]


class DjangoDataSetRepository(BaseDjangoRepository[DataSet], BaseDataSetRepository[DataSet]):
    pass


class DjangoAgentRepository(BaseDjangoRepository[Agent], BaseAgentRepository[Agent]):
    def get_agent_configuration_by_id(self, agent_id: int) -> Any:
        return self.get_by_id(agent_id).config
