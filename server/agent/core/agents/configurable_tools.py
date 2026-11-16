import logging
from collections.abc import Iterator

from suvereo_common.agents import BaseAgent
from suvereo_common.config import AgentToolConfig, ToolConfig
from suvereo_common.tools.base import BaseTool
from utils.functions import get_model_descriptor_default_value_from_class, get_model_descriptor_from_class_field

from agent.agentic_execution.registry import AgenticExecutionDefinitionRegistry

logger = logging.getLogger(__name__)

CONVERSATIONS = "Conversations"


class ConfigurableTools:
    @classmethod
    def for_agent(cls, agent_class: type[BaseAgent]) -> dict[str, type[BaseTool]]:
        return cls._first_by_name(cls._tool_sets(agent_class))

    @classmethod
    def schema(cls, agent_class: type[BaseAgent]) -> dict[str, dict]:
        tool_sets = cls._tool_sets(agent_class)
        used_by = cls._used_by(tool_sets)
        return {
            name: {
                "title": cls.title(name),
                "used_by": used_by[name],
                "fields": get_model_descriptor_from_class_field(tool_class, "CONFIGURATION_ARGS"),
            }
            for name, tool_class in cls._first_by_name(tool_sets).items()
        }

    @classmethod
    def defaults(cls, agent_class: type[BaseAgent]) -> dict[str, dict]:
        return {
            name: get_model_descriptor_default_value_from_class(tool_class, "CONFIGURATION_ARGS")
            for name, tool_class in cls.for_agent(agent_class).items()
        }

    @classmethod
    def conflicts(cls, agent_class: type[BaseAgent]) -> list[str]:
        return [
            f"Agent '{agent_class.AGENT_KEY}' or its executions or sub-agents define tool '{name}' with different settings "
            f"({', '.join(tool.__name__ for tool in tools)}); give the tools different NAMEs."
            for name, tools in cls._by_name(cls._tool_sets(agent_class)).items()
            if len({tool.CONFIGURATION_ARGS for tool in tools}) > 1
        ] + [
            f"Agent '{agent_class.AGENT_KEY}' reaches itself through its sub-agents "
            f"({' -> '.join(agent.__name__ for agent in cycle)}); remove one of the agent tools."
            for cycle in cls._sub_agent_cycles(agent_class)
        ]

    @staticmethod
    def title(name: str) -> str:
        return name.replace("_", " ").capitalize()

    @classmethod
    def _first_by_name(cls, tool_sets: list[tuple[str, list[ToolConfig]]]) -> dict[str, type[BaseTool]]:
        return {name: tools[0] for name, tools in cls._by_name(tool_sets).items()}

    @staticmethod
    def _by_name(tool_sets: list[tuple[str, list[ToolConfig]]]) -> dict[str, list[type[BaseTool]]]:
        by_name: dict[str, list[type[BaseTool]]] = {}
        for _, tool_configs in tool_sets:
            for tool_config in tool_configs:
                tool_class = tool_config.tool_class
                if tool_class.CONFIGURATION_ARGS is not None and tool_class not in by_name.get(tool_class.NAME, []):
                    by_name.setdefault(tool_class.NAME, []).append(tool_class)
        return by_name

    @staticmethod
    def _used_by(tool_sets: list[tuple[str, list[ToolConfig]]]) -> dict[str, list[str]]:
        used_by: dict[str, list[str]] = {}
        for user, tool_configs in tool_sets:
            for name in dict.fromkeys(tool_config.tool_class.NAME for tool_config in tool_configs):
                used_by.setdefault(name, []).append(user)
        return used_by

    @classmethod
    def _tool_sets(cls, agent_class: type[BaseAgent]) -> list[tuple[str, list[ToolConfig]]]:
        own = cls._own_tool_sets(agent_class)
        return own + cls._sub_agent_tool_sets(own, chain=(agent_class,))

    @classmethod
    def _sub_agent_tool_sets(
        cls, tool_sets: list[tuple[str, list[ToolConfig]]], chain: tuple[type[BaseAgent], ...]
    ) -> list[tuple[str, list[ToolConfig]]]:
        found = []
        for sub_agent in cls._sub_agents(tool_sets):
            if sub_agent in chain:
                continue
            sub_agent_tools = [(f"Sub-agent {sub_agent.NAME}", sub_agent.TOOLS or [])]
            found += sub_agent_tools + cls._sub_agent_tool_sets(sub_agent_tools, chain + (sub_agent,))
        return found

    @classmethod
    def _sub_agent_cycles(cls, agent_class: type[BaseAgent]) -> list[tuple[type[BaseAgent], ...]]:
        def walk(
            tool_sets: list[tuple[str, list[ToolConfig]]], chain: tuple[type[BaseAgent], ...]
        ) -> Iterator[tuple[type[BaseAgent], ...]]:
            for sub_agent in cls._sub_agents(tool_sets):
                if sub_agent in chain:
                    yield chain + (sub_agent,)
                else:
                    yield from walk([("", sub_agent.TOOLS or [])], chain + (sub_agent,))

        return list(walk(cls._own_tool_sets(agent_class), (agent_class,)))

    @staticmethod
    def _sub_agents(tool_sets: list[tuple[str, list[ToolConfig]]]) -> list[type[BaseAgent]]:
        return list(
            dict.fromkeys(
                tool_config.agent_class
                for _, tool_configs in tool_sets
                for tool_config in tool_configs
                if isinstance(tool_config, AgentToolConfig)
            )
        )

    @staticmethod
    def _own_tool_sets(agent_class: type[BaseAgent]) -> list[tuple[str, list[ToolConfig]]]:
        agent_tools = agent_class.TOOLS or []
        try:
            executions = AgenticExecutionDefinitionRegistry().get_by_agent_type(agent_class.AGENT_KEY)
        except Exception:
            logger.exception(
                "Could not load the executions of agent %s; using its own tools only", agent_class.AGENT_KEY
            )
            executions = []
        return [
            (CONVERSATIONS, agent_tools),
            *(
                (execution.NAME, agent_tools if execution.TOOLS is None else execution.TOOLS)
                for execution in executions
            ),
        ]
