import builtins
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")


class BaseRepository(ABC, Generic[T]):
    def __init__(self, model: type[T]):
        self.model = model

    @abstractmethod
    def get_by_id(self, pk: int) -> T | None:
        pass

    @abstractmethod
    def list(self) -> list[T]:
        pass

    @abstractmethod
    def filter(self, **kwargs) -> builtins.list[T]:
        pass

    @abstractmethod
    def create(self, **kwargs) -> T:
        pass

    @abstractmethod
    def update(self, pk: int, **kwargs) -> T:
        pass

    @abstractmethod
    def delete(self, pk: int) -> bool:
        pass


class BaseUserRepository(BaseRepository[T], ABC, Generic[T, U]):
    @abstractmethod
    def get_user_dataset(self, user_id: Any, data_set_id: Any) -> U:
        pass


class BaseMessageRepository(BaseRepository[T], ABC):
    pass


class BaseConversationRepository(BaseRepository[T], ABC):
    @abstractmethod
    def get_data_set_id(self, conversation_id: Any) -> Any:
        pass

    @abstractmethod
    def get_agent_id(self, conversation_id: Any) -> Any:
        pass

    @abstractmethod
    def list_files(self, conversation_id: Any) -> list[Any]:
        pass

    @abstractmethod
    def get_file_objects(self, conversation_id: Any, file_ids: list[Any]) -> list[Any]:
        pass


class BaseDataSetRepository(BaseRepository[T], ABC):
    pass


class BaseAgentRepository(BaseRepository[T], ABC):
    @abstractmethod
    def get_agent_configuration_by_id(self, conversation_id: Any) -> Any:
        pass
