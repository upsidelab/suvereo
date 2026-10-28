from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, Type, TypeVar

from ..agentic_execution.memory import ToolScratchpad
from ..agents import BaseAgent
from ..config.base import AgentConfig

ConfigT = TypeVar("ConfigT", bound=AgentConfig)


class BaseAgentBuilder(ABC, Generic[ConfigT]):
    """Contract every agent builder must satisfy.

    This is the full extent of what the framework requires from a builder: the
    constructor signature below and a ``build()`` returning a ready agent. A
    agent's ``BUILDER_CLASS`` may point at any class honouring this
    contract. For the config-driven default implementation with overridable
    steps, see :class:`suvereo_common.builder.AgentBuilder`.
    """

    def __init__(
        self,
        agent_class: Type[BaseAgent],
        config: ConfigT,
        conversation_id: Any,
        streaming: bool = False,
        tool_scratchpad: Optional[ToolScratchpad] = None,
    ):
        self._agent_class = agent_class
        self._config = config
        self.conversation_id = conversation_id
        self.streaming = streaming
        self._tool_scratchpad = tool_scratchpad

    @abstractmethod
    def build(self) -> BaseAgent:
        """Build and return a fully wired agent for the conversation."""
