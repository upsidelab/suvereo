from collections.abc import Iterable
from copy import deepcopy

from pydantic import ValidationError
from suvereo_common.agents import BaseAgent
from suvereo_common.tools.base import BaseTool

from agent.core.agents.configurable_tools import ConfigurableTools
from agent.core.registries.agents.agent_registry import AgentRegistry, AgentRegistryError
from agent.models import Agent


class AgentVerificationService:
    def __init__(self):
        self._agent_classes: dict[str, type[BaseAgent] | None] = {}
        self._configurable_tools: dict[str, dict[str, type[BaseTool]]] = {}

    def verify(self, agents: Iterable[Agent]) -> None:
        changed = []
        for agent in agents:
            corrupted = not self.is_valid(agent)
            if agent.corrupted != corrupted:
                agent.corrupted = corrupted
                changed.append(agent)
        Agent.objects.bulk_update(changed, ["corrupted"])

    def is_valid(self, agent: Agent) -> bool:
        agent_class = self._agent_class(agent.agent_type)
        if agent_class is None:
            return False
        config = deepcopy(agent.config)
        tools_config = config.pop("tools", {})
        try:
            self._validate_agent_config(agent_class, config)
            self._validate_tools_config(tools_config, self._configurable_tools[agent.agent_type])
        except (ValidationError, TypeError, ValueError):
            return False
        return True

    def _agent_class(self, agent_type: str) -> type[BaseAgent] | None:
        if agent_type not in self._agent_classes:
            try:
                agent_class = AgentRegistry().get_agent_class_by_type(agent_type=agent_type)
            except AgentRegistryError:
                agent_class = None
            else:
                self._configurable_tools[agent_type] = ConfigurableTools.for_agent(agent_class)
            self._agent_classes[agent_type] = agent_class
        return self._agent_classes[agent_type]

    @staticmethod
    def _validate_agent_config(agent_class: type[BaseAgent], config: dict) -> None:
        for key, value in config.items():
            field = getattr(agent_class, key.upper(), None)
            if field is not None:
                field(**value)

    @staticmethod
    def _validate_tools_config(tools_config, configurable_tools: dict[str, type[BaseTool]]) -> None:
        if not isinstance(tools_config, dict):
            raise TypeError("Tool configurations must be keyed by tool name")

        if unknown := set(tools_config) - set(configurable_tools):
            raise ValueError(f"Unknown or non-configurable tools: {', '.join(sorted(unknown))}")

        for name, tool_class in configurable_tools.items():
            settings = tools_config.get(name, {})
            if not isinstance(settings, dict):
                raise TypeError(f"Settings of tool {name} must be an object")
            tool_class.CONFIGURATION_ARGS(**settings)
