from unittest.mock import patch

import pytest
from pydantic import Field
from suvereo_common.config import FunctionToolConfig
from suvereo_common.tools import BaseFunctionTool
from suvereo_common.utils import RequiredFieldsModel

from agent.core.registries.agents.agent_registry import AgentRegistry
from agent.models import Agent
from agent.services import AgentPreconfigurationService
from catalog.models import DataSet

pytestmark = pytest.mark.django_db


class ToolArgs(RequiredFieldsModel):
    with_default: str = Field(description="description", title="title", default="default")


class DummyTool(BaseFunctionTool):
    NAME = "dummy_tool"
    CONFIGURATION_ARGS = ToolArgs


class OtherDummyTool(DummyTool):
    NAME = "other_dummy_tool"


class AgentArgs(RequiredFieldsModel):
    with_default: str = Field(description="description", title="title", default="default")


class AgentArgsWithoutDefaults(RequiredFieldsModel):
    with_default: str = Field(description="description", title="title", default="default")
    without_default: str = Field(description="description", title="title")


class PromptInput(RequiredFieldsModel):
    with_default: str = Field(description="description", title="title", default="default")


class MockAgentClass:
    AGENT_KEY = "dummy_agent"
    NAME = "Dummy Agent"
    AGENT_ARGS = AgentArgs
    PROMPT_INPUT = PromptInput
    TOOLS = [FunctionToolConfig(tool_class=DummyTool), FunctionToolConfig(tool_class=OtherDummyTool)]
    FILE_UPLOAD = False


class MockAgentClassFileUpload(MockAgentClass):
    FILE_UPLOAD = True


class MockAgentClassWithoutDefaults:
    AGENT_KEY = "dummy_agent_without_defaults"
    NAME = "Dummy Agent Without Defaults"
    AGENT_ARGS = AgentArgsWithoutDefaults
    PROMPT_INPUT = None
    TOOLS = []
    FILE_UPLOAD = False


EXPECTED_AGENT_CONFIG = {
    "agent_args": {"with_default": "default"},
    "prompt_input": {"with_default": "default"},
    "tools": {"dummy_tool": {"with_default": "default"}, "other_dummy_tool": {"with_default": "default"}},
}


@pytest.fixture(autouse=True)
def django_settings(settings):
    settings.AVAILABLE_AGENTS = [
        "dummy_agent_directory_path.DummyAgent"
    ]


class TestAgentPreconfigurationService:
    @pytest.fixture
    def dataset(self):
        return DataSet.objects.create(name="Test Dataset")

    @pytest.mark.parametrize(
        "agent_class, expected_file_upload_flag",
        [
            (MockAgentClass, False),
            (MockAgentClassFileUpload, True),
        ],
    )
    @patch.object(AgentRegistry, "get_plugin_classes")
    def test_preconfigure_available_agents_creates_agents(
        self, mock_agent_registry, agent_class, expected_file_upload_flag, dataset
    ):
        mock_agent_registry.return_value = [agent_class]

        AgentPreconfigurationService.preconfigure_available_agents(dataset)

        agent = Agent.objects.filter(dataset=dataset).first()
        assert agent
        assert agent.config == EXPECTED_AGENT_CONFIG
        assert agent.file_upload is expected_file_upload_flag

    @patch.object(AgentRegistry, "get_plugin_classes")
    def test_preconfigure_available_agents_skip_agents_without_defaults(self, mock_agent_registry, dataset):
        mock_agent_registry.return_value = [MockAgentClassWithoutDefaults]

        AgentPreconfigurationService.preconfigure_available_agents(dataset)
        assert Agent.objects.filter(dataset=dataset).count() == 0

    @patch.object(AgentRegistry, "get_plugin_classes")
    def test_preconfigure_available_agents_skips_existing_agent(self, mock_agent_registry, dataset):
        Agent.objects.create(
            name="Existing Dummy Agent",
            description="Existing",
            config={"foo": "bar"},
            dataset=dataset,
            agent_type="dummy_agent",
        )
        mock_agent_registry.return_value = [MockAgentClass]

        AgentPreconfigurationService.preconfigure_available_agents(dataset)

        assert Agent.objects.filter(dataset=dataset, agent_type="dummy_agent").count() == 1