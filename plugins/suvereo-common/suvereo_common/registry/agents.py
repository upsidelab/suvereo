from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from suvereo_common.builder import BaseAgentBuilder

T = TypeVar("T", bound=BaseAgentBuilder)


class BaseAgentRegistry(ABC, Generic[T]):
    """Loads agent builder classes."""

    def __init__(self, agents_config: dict[Any, Any]):
        self._agents_config = agents_config

    @abstractmethod
    def get_builder_by_name(self, name: str) -> type[T]:
        """Return the builder class with this name."""
