from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Optional, Type

if TYPE_CHECKING:
    from ..builder import BaseAgentBuilder
    from ..config import AgentConfig


class ConfigType(StrEnum):
    """Registry of valid agent configuration context types."""

    CONVERSATION = "conversation"
    AGENTIC_EXECUTION_DEFINITION = "agentic_execution_definition"


class BaseAgentConfigProvider(ABC):
    """Interface for providing agent configuration based on the call context.

    Agent plugins export a subclass of this from their ``__init__.py``. The
    agent registry discovers it at runtime and calls :meth:`get_config` with
    the appropriate ``config_type`` so the plugin can return a context-specific
    configuration (e.g. a different system prompt for agentic execution runs).

    Plugins that do not need context-specific configs can ignore the
    ``config_type`` argument and always return the same configuration.
    """

    #: Builder class used to assemble this agent. Declare it when the agent needs a
    #: dedicated builder (e.g. a vertical's builder wiring domain-specific retrievers).
    #: Left as None, the registry falls back to the framework's default builder.
    BUILDER_CLASS: Optional[Type["BaseAgentBuilder"]] = None

    @abstractmethod
    def get_config(self, config_type: ConfigType = ConfigType.CONVERSATION) -> "AgentConfig":
        """Return the agent configuration for the given context type.

        Args:
            config_type: :attr:`ConfigType.CONVERSATION` for interactive user
                conversations, :attr:`ConfigType.AGENTIC_EXECUTION_DEFINITION` for
                autonomous agentic execution runs.

        Returns:
            AgentConfig: fully populated configuration ready for the builder.
        """
        pass
