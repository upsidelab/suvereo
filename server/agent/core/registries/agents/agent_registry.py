from abc import ABC, abstractmethod
from typing import List, Optional, Type

from django.conf import settings
from suvereo_common.agentic_execution.memory import ToolScratchpad
from suvereo_common.agents import BaseAgent
from suvereo_common.builder import AgentBuilder
from utils.base_registry import BaseRegistry

from agent.core.agents.config_overrides import AgentConfigOverrides
from agent.core.agents.default_config import merge_config
from agent.models import Conversation


class AgentRegistryError(Exception):
    """Base exception for all AgentRegistry errors."""


class AgentNotFoundError(AgentRegistryError):
    """Raised when agent type is not found in config."""


class AgentConfigError(AgentRegistryError):
    """Raised when agent configuration is missing or invalid."""


class BaseAgentRegistry(ABC, BaseRegistry[BaseAgent]):
    plugin_base = BaseAgent

    @abstractmethod
    def get_conversation_agent(self, *args, **kwargs) -> BaseAgent:
        pass

    @abstractmethod
    async def aget_conversation_agent(self, *args, **kwargs) -> BaseAgent:
        pass

    @abstractmethod
    def get_agent_class_by_type(self, *args, **kwargs) -> Type[BaseAgent]:
        pass


class AgentRegistry(BaseAgentRegistry):

    def get_conversation_agent(
        self,
        conversation: Conversation,
        streaming: bool,
        tool_scratchpad: Optional[ToolScratchpad] = None,
        overrides: Optional[AgentConfigOverrides] = None,
    ) -> BaseAgent:
        try:
            builder = self._build_agent_builder(conversation, streaming, tool_scratchpad, overrides)
            return builder.build()
        except Exception as e:
            raise AgentRegistryError(f"Failed to build agent for conversation {conversation.id}") from e

    async def aget_conversation_agent(
        self,
        conversation: Conversation,
        streaming: bool,
        tool_scratchpad: Optional[ToolScratchpad] = None,
        overrides: Optional[AgentConfigOverrides] = None,
    ) -> BaseAgent:
        try:
            builder = self._build_agent_builder(conversation, streaming, tool_scratchpad, overrides)
            return await builder.abuild()
        except Exception as e:
            raise AgentRegistryError(f"Failed to build agent for conversation {conversation.id}") from e

    def _build_agent_builder(
        self,
        conversation: Conversation,
        streaming: bool,
        tool_scratchpad: Optional[ToolScratchpad],
        overrides: Optional[AgentConfigOverrides] = None,
    ):
        agent_class = self.get_agent_class_by_type(conversation.agent.agent_type)
        builder_cls = agent_class.BUILDER_CLASS or AgentBuilder
        config = merge_config(partial=agent_class.get_config())
        if overrides:
            config = overrides.apply(config)
        return builder_cls(
            agent_class=agent_class,
            config=config,
            conversation_id=conversation.id,
            streaming=streaming,
            tool_scratchpad=tool_scratchpad,
        )

    def get_agent_class_by_type(self, agent_type: str) -> Type[BaseAgent]:
        agents = [agent for agent in self.get_plugin_classes() if agent.AGENT_KEY == agent_type]

        if not agents:
            raise AgentNotFoundError(f"Could not find agent type '{agent_type}'.")

        return agents[0]

    def get_plugin_classes(self) -> List[Type[BaseAgent]]:
        return [self._get_plugin_class_by_path(path) for path in self._get_plugin_paths()]

    @staticmethod
    def _get_plugin_paths() -> List[str]:
        return settings.AVAILABLE_AGENTS
