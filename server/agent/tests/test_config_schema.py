from unittest.mock import patch

import pytest
from model_bakery import baker
from pydantic import Field
from suvereo_common.config import FunctionToolConfig
from suvereo_common.tools import BaseFunctionTool
from suvereo_common.utils import RequiredFieldsModel

from agent.models.agent import Agent
from agent.serializers.configuration import AgentSerializer, agent_type_config_schema, agent_type_display_name
from catalog.models import DataSet

pytestmark = pytest.mark.django_db


class ToolArgs(RequiredFieldsModel):
    tool_setting: str = Field(description="A tool setting", title="Tool setting")


class DummyTool(BaseFunctionTool):
    NAME = "dummy_tool"
    CONFIGURATION_ARGS = ToolArgs


class UnconfigurableTool(BaseFunctionTool):
    NAME = "unconfigurable_tool"
    CONFIGURATION_ARGS = None


class AgentArgs(RequiredFieldsModel):
    text_arg: str = Field(description="A text argument", title="Text argument")
    number_arg: int = Field(description="A number argument", title="Number argument", default=1)


class PromptInput(RequiredFieldsModel):
    prompt_arg: str = Field(description="A prompt argument", title="Prompt argument")


class DummyAgent:
    AGENT_KEY = "dummy_agent"
    NAME = "Dummy Agent"
    AGENT_ARGS = AgentArgs
    PROMPT_INPUT = PromptInput
    TOOLS = [FunctionToolConfig(tool_class=DummyTool), FunctionToolConfig(tool_class=UnconfigurableTool)]
    FILE_UPLOAD = False


@pytest.fixture
def agent():
    return baker.make(
        Agent,
        dataset=baker.make(DataSet),
        agent_type="dummy_agent",
        deleted_at=None,
        config={
            "agent_args": {"text_arg": "hello", "number_arg": 7},
            "prompt_input": {"prompt_arg": "prompt"},
            "tools": {"dummy_tool": {"tool_setting": "on"}},
        },
    )


@pytest.fixture
def installed_agent_class():
    with patch(
        "agent.serializers.configuration.AgentRegistry.get_agent_class_by_type",
        return_value=DummyAgent,
    ) as mocked:
        yield mocked


class TestAgentTypeConfigSchema:
    def test_groups_the_descriptors_the_way_the_stored_config_is_grouped(self):
        schema = agent_type_config_schema(DummyAgent)

        assert list(schema.keys()) == ["agent_args", "prompt_input", "tools"]
        assert list(schema["agent_args"].keys()) == ["text_arg", "number_arg"]
        assert list(schema["tools"]) == ["dummy_tool"]

    def test_tools_are_keyed_by_name_with_a_title_and_their_fields(self):
        tool = agent_type_config_schema(DummyAgent)["tools"]["dummy_tool"]

        assert tool["title"] == "Dummy tool"
        assert list(tool["fields"]) == ["tool_setting"]
        assert tool["fields"]["tool_setting"]["title"] == "Tool setting"

    def test_descriptors_carry_the_title_description_type_and_required_flag(self):
        text_arg = agent_type_config_schema(DummyAgent)["agent_args"]["text_arg"]

        assert text_arg["title"] == "Text argument"
        assert text_arg["description"] == "A text argument"
        assert text_arg["type"] == {"container": None, "inner_type": "str"}
        assert text_arg["required"] is True

    def test_required_is_false_for_a_field_with_a_default(self):
        assert agent_type_config_schema(DummyAgent)["agent_args"]["number_arg"]["required"] is False


class TestAgentTypeDisplayName:
    def test_uses_the_installed_plugin_name(self, agent, installed_agent_class):
        assert agent_type_display_name(agent) == "Dummy Agent"

    def test_falls_back_to_the_stored_type_key(self, agent):
        with patch(
            "agent.serializers.configuration.AgentRegistry.get_agent_class_by_type",
            side_effect=KeyError("dummy_agent"),
        ):
            assert agent_type_display_name(agent) == "dummy_agent"


class TestAgentSerializer:
    def test_serves_the_schema_of_the_agents_own_type(self, agent, installed_agent_class):
        data = AgentSerializer(agent).data

        assert data["agent_type_name"] == "Dummy Agent"
        assert data["config_schema"] == agent_type_config_schema(DummyAgent)

    def test_an_agent_whose_plugin_is_gone_has_no_schema(self, agent):
        with patch(
            "agent.serializers.configuration.AgentRegistry.get_agent_class_by_type",
            side_effect=KeyError("dummy_agent"),
        ):
            assert AgentSerializer(agent).data["config_schema"] == {}
