import logging

from django.db import migrations

logger = logging.getLogger(__name__)


def _agent_tools(agent_type):
    from agent.core.registries.agents.agent_registry import AgentNotFoundError, AgentRegistry

    try:
        return [tool_config.tool_class for tool_config in AgentRegistry().get_agent_class_by_type(agent_type).TOOLS]
    except AgentNotFoundError:
        logger.warning("Agent type %s is not installed; its agents keep their tool settings list", agent_type)
        return None


def tools_list_to_map(apps, schema_editor):
    Agent = apps.get_model("agent", "Agent")
    for agent in Agent.objects.all():
        stored = agent.config.get("tools")
        tools = _agent_tools(agent.agent_type)
        if not isinstance(stored, list) or tools is None:
            continue
        agent.config["tools"] = {
            tool.NAME: settings for tool, settings in zip(tools, stored) if tool.CONFIGURATION_ARGS is not None
        }
        agent.save(update_fields=["config"])


def tools_map_to_list(apps, schema_editor):
    Agent = apps.get_model("agent", "Agent")
    for agent in Agent.objects.all():
        stored = agent.config.get("tools")
        tools = _agent_tools(agent.agent_type)
        if not isinstance(stored, dict) or tools is None:
            continue
        agent.config["tools"] = [stored.get(tool.NAME, {}) for tool in tools]
        agent.save(update_fields=["config"])


class Migration(migrations.Migration):
    dependencies = [
        ("agent", "0034_agent_tool_providing_integrations"),
    ]

    operations = [
        migrations.RunPython(tools_list_to_map, tools_map_to_list),
    ]
