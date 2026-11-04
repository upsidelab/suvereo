from importlib import import_module
from unittest.mock import patch

import pytest
from django.apps import apps
from model_bakery import baker
from pydantic import Field
from suvereo_common.config import FunctionToolConfig
from suvereo_common.tools import BaseFunctionTool
from suvereo_common.utils import RequiredFieldsModel

from agent.core.registries.agents.agent_registry import AgentNotFoundError
from agent.models import Agent

pytestmark = pytest.mark.django_db

migration = import_module("agent.migrations.0035_key_tool_configuration_by_tool_name")


class ProxyArgs(RequiredFieldsModel):
    proxy: str = Field(title="Proxy", description="Proxy URL", default="")


class ProxiedTool(BaseFunctionTool):
    NAME = "proxied"
    CONFIGURATION_ARGS = ProxyArgs


class PlainTool(BaseFunctionTool):
    NAME = "plain"
    CONFIGURATION_ARGS = None


class InstalledAgent:
    TOOLS = [FunctionToolConfig(tool_class=PlainTool), FunctionToolConfig(tool_class=ProxiedTool)]


def _agent_class_by_type(agent_type: str):
    if agent_type == "broken":
        raise ModuleNotFoundError("enthusiast_agent_broken")
    if agent_type != "installed":
        raise AgentNotFoundError(agent_type)
    return InstalledAgent


@pytest.fixture
def installed_agent():
    with patch(
        "agent.core.registries.agents.agent_registry.AgentRegistry.get_agent_class_by_type",
        side_effect=_agent_class_by_type,
    ):
        yield


def _agent(agent_type: str, tools) -> Agent:
    return baker.make(Agent, agent_type=agent_type, config={"agent_args": {}, "tools": tools})


class TestToolConfigurationMigration:
    def test_a_list_becomes_a_map_of_the_configurable_tools_by_name(self, installed_agent):
        agent = _agent("installed", [{}, {"proxy": "http://proxy:8080"}])

        migration.tools_list_to_map(apps, None)

        agent.refresh_from_db()
        assert agent.config == {"agent_args": {}, "tools": {"proxied": {"proxy": "http://proxy:8080"}}}

    def test_an_agent_whose_type_is_not_installed_keeps_its_list(self, installed_agent):
        agent = _agent("removed", [{"proxy": "x"}])

        migration.tools_list_to_map(apps, None)

        agent.refresh_from_db()
        assert agent.config["tools"] == [{"proxy": "x"}]

    def test_an_agent_type_that_fails_to_load_stops_the_migration(self, installed_agent):
        _agent("broken", [{}])

        with pytest.raises(ModuleNotFoundError):
            migration.tools_list_to_map(apps, None)

    def test_reversing_restores_the_list_in_tool_order(self, installed_agent):
        agent = _agent("installed", {"proxied": {"proxy": "http://proxy:8080"}})

        migration.tools_map_to_list(apps, None)

        agent.refresh_from_db()
        assert agent.config["tools"] == [{}, {"proxy": "http://proxy:8080"}]
