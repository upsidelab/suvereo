from unittest.mock import patch

import pytest
from pydantic import BaseModel, Field
from suvereo_common.agents import BaseAgent
from suvereo_common.config import AgentToolConfig, FunctionToolConfig
from suvereo_common.tools import BaseAgentTool, BaseFunctionTool
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


class AskTool(BaseAgentTool):
    NAME = "ask"
    DESCRIPTION = "Asks a sub-agent"
    ARGS_SCHEMA = BaseModel
    RETURN_DIRECT = False

    def run(self):
        return ""


class SubAgent(BaseAgent):
    AGENT_KEY = "sub"
    NAME = "Research"
    SYSTEM_PROMPT = "Research."

    def get_answer(self, input_text: str) -> str:
        return input_text

    async def aget_answer(self, input_text: str) -> str:
        return input_text


class ResearchAgent(SubAgent):
    TOOLS = [FunctionToolConfig(tool_class=TokenTool), FunctionToolConfig(tool_class=StopTool)]


class ReviewAgent(SubAgent):
    NAME = "Review"
    TOOLS = [AgentToolConfig(tool_class=AskTool, agent_class=ResearchAgent)]


class ClashingSubAgent(SubAgent):
    NAME = "Clashing"
    TOOLS = [FunctionToolConfig(tool_class=ClashingTool)]


class LoopAgent(SubAgent):
    NAME = "Loop"


class OtherLoopAgent(SubAgent):
    NAME = "Other loop"
    TOOLS = [AgentToolConfig(tool_class=AskTool, agent_class=LoopAgent)]


LoopAgent.TOOLS = [AgentToolConfig(tool_class=AskTool, agent_class=OtherLoopAgent)]


def agent_with(*tools) -> type:
    return type("Parent", (), {"AGENT_KEY": "stub", "TOOLS": [FunctionToolConfig(tool_class=ProxiedTool), *tools]})


def ask(agent_class: type[BaseAgent]) -> AgentToolConfig:
    return AgentToolConfig(tool_class=AskTool, agent_class=agent_class)


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


class TestSubAgentTools:
    def test_a_sub_agents_configurable_tools_are_configured_on_the_agent(self, executions):
        assert ConfigurableTools.for_agent(agent_with(ask(ResearchAgent))) == {
            "proxied": ProxiedTool,
            "token_tool": TokenTool,
        }

    def test_the_schema_lists_the_sub_agent_as_a_user_of_its_tools(self, executions):
        schema = ConfigurableTools.schema(agent_with(ask(ResearchAgent)))

        assert schema["token_tool"]["used_by"] == ["Sub-agent Research"]

    def test_defaults_cover_the_sub_agents_tools(self, executions):
        assert ConfigurableTools.defaults(agent_with(ask(ResearchAgent))) == {
            "proxied": {"proxy": ""},
            "token_tool": {},
        }

    def test_the_tools_of_a_sub_agents_sub_agent_count_too(self, executions):
        schema = ConfigurableTools.schema(agent_with(ask(ReviewAgent)))

        assert schema["token_tool"]["used_by"] == ["Sub-agent Research"]

    def test_a_sub_agent_of_an_execution_counts_too(self, executions):
        executions.return_value = [type("Delegates", (), {"NAME": "Delegates", "TOOLS": [ask(ResearchAgent)]})]

        assert "token_tool" in ConfigurableTools.for_agent(StubAgent)

    def test_a_sub_agent_tool_named_like_one_of_the_agent_with_other_settings_is_a_conflict(self, executions):
        [conflict] = ConfigurableTools.conflicts(agent_with(ask(ClashingSubAgent)))

        assert "'proxied'" in conflict and "ClashingTool" in conflict

    def test_sub_agents_that_reach_back_to_each_other_are_a_conflict(self, executions):
        [conflict] = ConfigurableTools.conflicts(agent_with(ask(LoopAgent)))

        assert "Parent -> LoopAgent -> OtherLoopAgent -> LoopAgent" in conflict

    def test_sub_agents_that_reach_back_to_each_other_are_walked_once(self, executions):
        assert ConfigurableTools.for_agent(agent_with(ask(LoopAgent))) == {"proxied": ProxiedTool}


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
            side_effect=TypeError("BrokenExecution cannot be loaded"),
        ):
            [warning] = check_tool_settings_conflicts(None)

        assert warning.id == "agent.W001"
        assert "BrokenExecution cannot be loaded" in warning.msg
