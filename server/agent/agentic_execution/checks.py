from django.core.checks import CheckMessage, Error, Warning

from agent.agentic_execution.registry import AgenticExecutionDefinitionRegistry
from agent.core.agents.configurable_tools import ConfigurableTools
from agent.core.registries.agents.agent_registry import AgentRegistry

TOOL_SETTINGS_CONFLICT = "agent.E001"
PLUGINS_NOT_LOADED = "agent.W001"


def check_tool_settings_conflicts(app_configs, **kwargs) -> list[CheckMessage]:
    try:
        AgenticExecutionDefinitionRegistry().get_all()
        agent_classes = AgentRegistry().get_plugin_classes()
        return [
            Error(message, id=TOOL_SETTINGS_CONFLICT)
            for agent_class in agent_classes
            for message in ConfigurableTools.conflicts(agent_class)
        ]
    except Exception as e:
        return [Warning(f"Tool settings were not checked: {type(e).__name__}: {e}", id=PLUGINS_NOT_LOADED)]
