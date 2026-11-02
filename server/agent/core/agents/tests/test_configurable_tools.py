from unittest.mock import patch

import pytest
from pydantic import Field
from suvereo_common.config import FunctionToolConfig
from suvereo_common.tools import BaseFunctionTool
from suvereo_common.utils import RequiredFieldsModel

from agent.agentic_execution.checks import check_tool_settings_conflicts
from agent.core.agents.configurable_tools import ConfigurableTools


class ProxyArgs(RequiredFieldsModel):
    proxy: str = Field(title="Proxy", description="Proxy URL", default="")


class TokenArgs(RequiredFieldsModel):
    token: str = Field(title="Token", description="API token")


class ProxiedTool(BaseFunctionTool):
    NAME = "proxied"
    CONFIGURATION_ARGS = ProxyArgs


class TokenTool(BaseFunctionTool):
    NAME = "token_tool"
    CONFIGURATION_ARGS = TokenArgs


class ClashingTool(BaseFunctionTool):
    NAME = "proxied"
    CONFIGURATION_ARGS = TokenArgs


class StopTool(BaseFunctionTool):
    NAME = "stop"
    CONFIGURATION_ARGS = None


class StubAgent:
    AGENT_KEY = "stub"
    TOOLS = [FunctionToolConfig(tool_class=ProxiedTool), FunctionToolConfig(tool_class=StopTool)]


class KeepsAgentTools:
    AGENT_KEY = "stub"
    NAME = "Keeps"
    TOOLS = None


class AddsTokenTool:
    AGENT_KEY = "stub"
    NAME = "Adds token"
    TOOLS = [FunctionToolConfig(tool_class=TokenTool), FunctionToolConfig(tool_class=StopTool)]


class Clashes:
    AGENT_KEY = "stub"
    NAME = "Clashes"
    TOOLS = [FunctionToolConfig(tool_class=ClashingTool)]


@pytest.fixture
def executions():
    with patch("agent.core.agents.configurable_tools.AgenticExecutionDefinitionRegistry.get_by_agent_type") as get:
        get.return_value = []
        yield get


class TestConfigurableTools:
    def test_without_executions_only_the_agents_configurable_tools_count(self, executions):
        assert ConfigurableTools.for_agent(StubAgent) == {"proxied": ProxiedTool}

    def test_a_configurable_tool_only_an_execution_runs_is_configured_on_the_agent(self, executions):
        executions.return_value = [AddsTokenTool]

        assert ConfigurableTools.for_agent(StubAgent) == {"proxied": ProxiedTool, "token_tool": TokenTool}
        executions.assert_called_with("stub")

    def test_the_schema_lists_where_each_tool_runs(self, executions):
        executions.return_value = [KeepsAgentTools, AddsTokenTool]

        schema = ConfigurableTools.schema(StubAgent)

        assert schema["proxied"]["used_by"] == ["Conversations", "Keeps"]
        assert schema["token_tool"] == {
            "title": "Token tool",
            "used_by": ["Adds token"],
            "fields": {
                "token": {
                    "type": {"container": None, "inner_type": "str"},
                    "description": "API token",
                    "title": "Token",
                    "required": True,
                }
            },
        }

    def test_executions_that_cannot_be_loaded_leave_the_agents_own_tools(self, executions):
        executions.side_effect = ModuleNotFoundError("broken_execution")

        assert ConfigurableTools.for_agent(StubAgent) == {"proxied": ProxiedTool}

    def test_defaults_cover_the_execution_tools(self, executions):
        executions.return_value = [AddsTokenTool]

        assert ConfigurableTools.defaults(StubAgent) == {"proxied": {"proxy": ""}, "token_tool": {}}

    def test_one_name_with_different_settings_is_a_conflict(self, executions):
        executions.return_value = [Clashes]

        [conflict] = ConfigurableTools.conflicts(StubAgent)

        assert "'stub'" in conflict and "'proxied'" in conflict and "ClashingTool" in conflict

    def test_the_same_tool_in_the_agent_and_an_execution_is_no_conflict(self, executions):
        executions.return_value = [KeepsAgentTools]

        assert ConfigurableTools.conflicts(StubAgent) == []


class TestToolSettingsConflictsCheck:
    def test_reports_each_conflict_as_an_error(self, executions):
        executions.return_value = [Clashes]

        with patch("agent.agentic_execution.checks.AgentRegistry.get_plugin_classes", return_value=[StubAgent]):
            [error] = check_tool_settings_conflicts(None)

        assert error.id == "agent.E001"
        assert "'proxied'" in error.msg

    def test_an_agent_that_cannot_be_loaded_is_a_warning(self):
        with patch(
            "agent.agentic_execution.checks.AgentRegistry.get_plugin_classes", side_effect=ImportError("no module")
        ):
            [warning] = check_tool_settings_conflicts(None)

        assert (warning.id, warning.is_serious()) == ("agent.W001", False)
        assert "ImportError: no module" in warning.msg

    def test_an_execution_that_cannot_be_loaded_is_a_warning(self):
        with patch(
            "agent.agentic_execution.checks.AgenticExecutionDefinitionRegistry.get_all",
            side_effect=TypeError("LegacyExecution sets EXTRA_TOOLS"),
        ):
            [warning] = check_tool_settings_conflicts(None)

        assert warning.id == "agent.W001"
        assert "EXTRA_TOOLS" in warning.msg
