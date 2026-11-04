from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

import pytest
from model_bakery import baker
from pydantic import BaseModel

from agent.core.registries.agents.agent_registry import AgentNotFoundError
from agent.models import Agent
from agent.services import AgentVerificationService

pytestmark = pytest.mark.django_db


class MockConfigurationArgs(BaseModel):
    value_1: str
    value_2: str = "default_value"


class MockToolConfigurationArgs(BaseModel):
    tool_value_1: str
    tool_value_2: bool = True


class MockToolClass:
    NAME = "tool_a"
    CONFIGURATION_ARGS = MockToolConfigurationArgs


class OtherMockToolClass(MockToolClass):
    NAME = "tool_b"


class MockAgentClass:
    AGENT_KEY = "test_agent"
    AGENT_ARGS = MockConfigurationArgs
    PROMPT_INPUT = MockConfigurationArgs
    TOOLS = [SimpleNamespace(tool_class=MockToolClass), SimpleNamespace(tool_class=OtherMockToolClass)]


@pytest.fixture
def config_dict() -> dict[Any, Any]:
    return {
        "agent_args": {"value_1": "value_1", "value_2": "value_2"},
        "prompt_input": {"value_1": "value_1", "value_2": "value_2"},
        "tools": {
            "tool_a": {"tool_value_1": "value_1", "tool_value_2": True},
            "tool_b": {"tool_value_1": "value_1", "tool_value_2": False},
        },
    }


class TestAgentVerificationService:
    AGENT_TYPE = "test_agent"
    MOCK_AGENT_CLASS = MockAgentClass

    @patch("agent.services.agent_verification_service.AgentRegistry")
    def test_verify_valid_configuration(self, mock_agent_registry, config_dict):
        valid_agent = baker.make(Agent, name="Valid Agent", agent_type=self.AGENT_TYPE, config=config_dict)

        mock_registry_instance = Mock()
        mock_registry_instance.get_agent_class_by_type.return_value = self.MOCK_AGENT_CLASS
        mock_agent_registry.return_value = mock_registry_instance

        AgentVerificationService().verify(Agent.objects.all())

        valid_agent.refresh_from_db()
        assert valid_agent.corrupted is False

    @patch("agent.services.agent_verification_service.AgentRegistry")
    def test_verify_clears_the_flag_of_an_agent_that_is_valid_again(self, mock_agent_registry, config_dict):
        agent = baker.make(Agent, agent_type=self.AGENT_TYPE, config=config_dict, corrupted=True)
        mock_agent_registry.return_value.get_agent_class_by_type.return_value = self.MOCK_AGENT_CLASS

        AgentVerificationService().verify(Agent.objects.all())

        agent.refresh_from_db()
        assert agent.corrupted is False

    @patch("agent.services.agent_verification_service.AgentRegistry")
    def test_verify_missing_field(self, mock_agent_registry, config_dict):
        config_dict["agent_args"] = {}
        corrupted_agent = baker.make(Agent, name="Corrupted Agent Args", agent_type=self.AGENT_TYPE, config=config_dict)

        mock_registry_instance = Mock()
        mock_registry_instance.get_agent_class_by_type.return_value = self.MOCK_AGENT_CLASS
        mock_agent_registry.return_value = mock_registry_instance

        AgentVerificationService().verify(Agent.objects.all())

        corrupted_agent.refresh_from_db()
        assert corrupted_agent.corrupted is True

    @patch("agent.services.agent_verification_service.AgentRegistry")
    def test_verify_invalid_type(self, mock_agent_registry, config_dict):
        config_dict["agent_args"]["value_1"] = 123
        corrupted_agent = baker.make(Agent, name="Corrupted Agent Args", agent_type=self.AGENT_TYPE, config=config_dict)

        mock_registry_instance = Mock()
        mock_registry_instance.get_agent_class_by_type.return_value = self.MOCK_AGENT_CLASS
        mock_agent_registry.return_value = mock_registry_instance

        AgentVerificationService().verify(Agent.objects.all())

        corrupted_agent.refresh_from_db()
        assert corrupted_agent.corrupted is True

    @patch("agent.services.agent_verification_service.AgentRegistry")
    def test_verify_missing_tool_config(self, mock_agent_registry, config_dict):
        config_dict["tools"] = {"tool_a": {"tool_value_1": "tool1", "tool_value_2": True}}
        corrupted_agent = baker.make(Agent, name="Corrupted Tools", agent_type=self.AGENT_TYPE, config=config_dict)

        mock_registry_instance = Mock()
        mock_registry_instance.get_agent_class_by_type.return_value = self.MOCK_AGENT_CLASS
        mock_agent_registry.return_value = mock_registry_instance

        AgentVerificationService().verify(Agent.objects.all())

        corrupted_agent.refresh_from_db()
        assert corrupted_agent.corrupted is True

    @patch("agent.services.agent_verification_service.AgentRegistry")
    def test_verify_invalid_tool_config_type(self, mock_agent_registry, config_dict):
        config_dict["tools"] = {
            "tool_a": {"tool_value_1": "tool1", "tool_value_2": True},
            "tool_b": {"tool_value_1": "tool1", "tool_value_2": "InvalidType"},
        }
        corrupted_agent = baker.make(Agent, name="Corrupted Tools", agent_type=self.AGENT_TYPE, config=config_dict)

        mock_registry_instance = Mock()
        mock_registry_instance.get_agent_class_by_type.return_value = self.MOCK_AGENT_CLASS
        mock_agent_registry.return_value = mock_registry_instance

        AgentVerificationService().verify(Agent.objects.all())

        corrupted_agent.refresh_from_db()
        assert corrupted_agent.corrupted is True

    @patch("agent.services.agent_verification_service.AgentRegistry")
    def test_verify_no_tool_configs(self, mock_agent_registry, config_dict):
        config_dict["tools"] = {}
        corrupted_agent = baker.make(Agent, name="Corrupted Tools", agent_type=self.AGENT_TYPE, config=config_dict)

        mock_registry_instance = Mock()
        mock_registry_instance.get_agent_class_by_type.return_value = self.MOCK_AGENT_CLASS
        mock_agent_registry.return_value = mock_registry_instance

        AgentVerificationService().verify(Agent.objects.all())

        corrupted_agent.refresh_from_db()
        assert corrupted_agent.corrupted is True

    @patch("agent.services.agent_verification_service.AgentRegistry")
    def test_verify_tool_configs_stored_as_a_list(self, mock_agent_registry, config_dict):
        config_dict["tools"] = list(config_dict["tools"].values())
        corrupted_agent = baker.make(Agent, name="Corrupted Tools", agent_type=self.AGENT_TYPE, config=config_dict)

        mock_registry_instance = Mock()
        mock_registry_instance.get_agent_class_by_type.return_value = self.MOCK_AGENT_CLASS
        mock_agent_registry.return_value = mock_registry_instance

        AgentVerificationService().verify(Agent.objects.all())

        corrupted_agent.refresh_from_db()
        assert corrupted_agent.corrupted is True

    @patch("agent.services.agent_verification_service.AgentRegistry")
    def test_verify_unknown_tool(self, mock_agent_registry, config_dict):
        config_dict["tools"]["renamed_tool"] = {}
        corrupted_agent = baker.make(Agent, name="Corrupted Tools", agent_type=self.AGENT_TYPE, config=config_dict)

        mock_registry_instance = Mock()
        mock_registry_instance.get_agent_class_by_type.return_value = self.MOCK_AGENT_CLASS
        mock_agent_registry.return_value = mock_registry_instance

        AgentVerificationService().verify(Agent.objects.all())

        corrupted_agent.refresh_from_db()
        assert corrupted_agent.corrupted is True

    @patch("agent.services.agent_verification_service.AgentRegistry")
    def test_verify_missing_agent_type(self, mock_agent_registry, config_dict):
        baker.make(Agent, agent_type=self.AGENT_TYPE, config=config_dict, _quantity=3)

        mock_registry_instance = Mock()
        mock_registry_instance.get_agent_class_by_type.side_effect = AgentNotFoundError()
        mock_agent_registry.return_value = mock_registry_instance

        AgentVerificationService().verify(Agent.objects.all())

        corrupted_agents = Agent.objects.filter(corrupted=True)
        assert corrupted_agents.count() == 3

    @patch("agent.services.agent_verification_service.AgentRegistry")
    def test_verify_multiple_corrupted_agents(self, mock_agent_registry, config_dict):
        config_dict["tools"] = {"tool_a": {}, "tool_b": {}}
        baker.make(Agent, name="Corrupted Agent 1", agent_type=self.AGENT_TYPE, config=config_dict)

        baker.make(Agent, name="Corrupted Agent 2", agent_type=self.AGENT_TYPE, config=config_dict)

        mock_registry_instance = Mock()
        mock_registry_instance.get_agent_class_by_type.return_value = self.MOCK_AGENT_CLASS
        mock_agent_registry.return_value = mock_registry_instance

        AgentVerificationService().verify(Agent.objects.all())

        corrupted_agents = Agent.objects.filter(corrupted=True)
        assert corrupted_agents.count() == 2

    @patch("agent.services.agent_verification_service.AgentRegistry")
    def test_verify_agent_type_caching(self, mock_agent_registry, config_dict):
        mock_registry_instance = Mock()
        mock_registry_instance.get_agent_class_by_type.return_value = self.MOCK_AGENT_CLASS
        mock_agent_registry.return_value = mock_registry_instance

        baker.make(Agent, name="Another Valid Agent", agent_type=self.AGENT_TYPE, config=config_dict)

        AgentVerificationService().verify(Agent.objects.all())

        mock_registry_instance.get_agent_class_by_type.assert_called_once_with(agent_type=self.AGENT_TYPE)

    @patch("agent.services.agent_verification_service.AgentRegistry")
    def test_verify_with_none_fields(self, mock_agent_registry):
        class MockAgentClassWithNoneFields:
            AGENT_KEY = "minimal_agent"
            AGENT_ARGS = None
            PROMPT_INPUT = None
            TOOLS = []

        mock_registry_instance = Mock()
        mock_registry_instance.get_agent_class_by_type.return_value = MockAgentClassWithNoneFields
        mock_agent_registry.return_value = mock_registry_instance

        baker.make(
            Agent,
            name="Minimal Agent",
            agent_type="minimal_agent",
            config={"agent_args": {}, "prompt_input": {}, "tools": {}},
        )

        AgentVerificationService().verify(Agent.objects.all())

        assert Agent.objects.filter(corrupted=True).count() == 0

    def test_verify_empty_database(self):
        Agent.objects.all().delete()

        with patch("agent.services.agent_verification_service.AgentRegistry") as mock_agent_registry:
            mock_registry_instance = Mock()
            mock_agent_registry.return_value = mock_registry_instance

            AgentVerificationService().verify(Agent.objects.all())
