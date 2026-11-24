import builtins
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")


class BaseRepository(ABC, Generic[T]):
    """Data access for one kind of record."""

    def __init__(self, model: type[T]):
        self.model = model

    @abstractmethod
    def get_by_id(self, pk: int) -> T | None:
        """Return the record with this primary key, or None."""

    @abstractmethod
    def list(self) -> list[T]:
        """Return all records."""

    @abstractmethod
    def filter(self, **kwargs: Any) -> builtins.list[T]:
        """Return the records matching the given field values."""

    @abstractmethod
    def create(self, **kwargs: Any) -> T:
        """Create a record from the given field values."""

    @abstractmethod
    def update(self, pk: int, **kwargs: Any) -> T:
        """Update the record with this primary key and return it."""

    @abstractmethod
    def delete(self, pk: int) -> bool:
        """Delete the record with this primary key; return whether one was deleted."""


class BaseUserRepository(BaseRepository[T], ABC, Generic[T, U]):
    """Data access for users."""

    @abstractmethod
    def get_user_dataset(self, user_id: Any, data_set_id: Any) -> U:
        """Return the user's membership in a data set."""


class BaseMessageRepository(BaseRepository[T], ABC):
    """Data access for conversation messages."""


class BaseConversationRepository(BaseRepository[T], ABC):
    """Data access for conversations."""

    @abstractmethod
    def get_data_set_id(self, conversation_id: Any) -> Any:
        """Return the id of the conversation's data set."""

    @abstractmethod
    def get_agent_id(self, conversation_id: Any) -> Any:
        """Return the id of the conversation's agent."""

    @abstractmethod
    def list_files(self, conversation_id: Any) -> list[Any]:
        """Return the files attached to the conversation."""

    @abstractmethod
    def get_file_objects(self, conversation_id: Any, file_ids: list[Any]) -> list[Any]:
        """Return the conversation's files with these ids, ready to pass to a language model."""


class BaseDataSetRepository(BaseRepository[T], ABC):
    """Data access for data sets."""


class BaseAgentRepository(BaseRepository[T], ABC):
    """Data access for agents."""

    @abstractmethod
    def get_agent_configuration_by_id(self, conversation_id: Any) -> Any:
        """Return the configuration of the conversation's agent."""
