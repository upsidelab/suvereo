from django.apps import AppConfig
from django.core.checks import register


class AgentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "agent"

    def ready(self):
        from agent.agentic_execution.checks import check_tool_settings_conflicts

        register(check_tool_settings_conflicts)
