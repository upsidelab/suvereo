from typing import Any
from unittest.mock import patch

import pytest
from pydantic import BaseModel
from rest_framework import serializers
from rest_framework.exceptions import APIException, ValidationError
from suvereo_common.config import FunctionToolConfig
from suvereo_common.tools import BaseFunctionTool

from agent.serializers.customs.fields import PydanticModelField, PydanticModelToolMapField


class DummySchema(BaseModel):
    value_1: str
    value_2: int


class BadSchema(BaseModel):
    value: int


class DummyTool(BaseFunctionTool):
    NAME = "dummy"
    CONFIGURATION_ARGS = DummySchema


class PlainTool(BaseFunctionTool):
    NAME = "plain"
    CONFIGURATION_ARGS = None


def get_model_serializer(
    agent_field_name: str,
    data,
):
    class FieldTestSerializer(serializers.Serializer):
        config = PydanticModelField(agent_field_name=agent_field_name)

    return FieldTestSerializer(data=data, context={"agent_type": "dummy_agent"})


def get_map_model_serializer(data: Any):
    class FieldTestSerializer(serializers.Serializer):
        config = PydanticModelToolMapField()

    return FieldTestSerializer(data=data, context={"agent_type": "dummy_agent"})


@pytest.fixture
def agent_context():
    return {"agent_type": "dummy_agent"}


@pytest.fixture
def available_agents():
    return [ "dummy_path.AgentClass" ]


@patch("agent.core.registries.agents.agent_registry.settings")
@patch("agent.serializers.customs.fields.AgentRegistry.get_agent_class_by_type")
def test_pydantic_model_field_valid(mock_import, mock_settings, available_agents):
    mock_settings.AVAILABLE_AGENTS = available_agents
    mock_import.return_value = type("Agent", (), {"AGENT_ARGS": DummySchema})
    input_data = {"config": {"value_1": "John", "value_2": 30}}

    serializer = get_model_serializer(agent_field_name="AGENT_ARGS", data=input_data)

    assert serializer.is_valid(raise_exception=True)


@patch("agent.core.registries.agents.agent_registry.settings")
@patch("agent.serializers.customs.fields.AgentRegistry.get_agent_class_by_type")
def test_pydantic_model_field_invalid_data(mock_import, mock_settings, available_agents):
    mock_settings.AVAILABLE_AGENTS = available_agents
    mock_import.return_value = type("Agent", (), {"AGENT_ARGS": DummySchema})
    input_data = {"config": {"value_1": "John"}}
    serializer = get_model_serializer(agent_field_name="AGENT_ARGS", data=input_data)

    with pytest.raises(ValidationError) as e:
        serializer.is_valid(raise_exception=True)
    assert "value_2" in str(e.value)


def test_pydantic_model_field_missing_context():
    field = PydanticModelField(agent_field_name="AGENT_ARGS")
    with pytest.raises(AssertionError) as e:
        field.to_internal_value({})
    assert "agent_type" in str(e.value)


@patch("agent.core.registries.agents.agent_registry.settings")
@patch("agent.serializers.customs.fields.AgentRegistry.get_agent_class_by_type", side_effect=ImportError("failed"))
def test_pydantic_model_field_import_error(mock_import, mock_settings, available_agents):
    mock_settings.AVAILABLE_AGENTS = available_agents
    input_data = {"config": {}}
    serializer = get_model_serializer(agent_field_name="AGENT_ARGS", data=input_data)

    with pytest.raises(APIException) as e:
        serializer.is_valid(raise_exception=True)
    assert "Error loading agent" in str(e.value)


class TestPydanticModelToolMapField:
    @pytest.fixture(autouse=True)
    def agent_class(self):
        agent_class = type(
            "Agent",
            (),
            {
                "AGENT_KEY": "dummy_agent",
                "TOOLS": [FunctionToolConfig(tool_class=PlainTool), FunctionToolConfig(tool_class=DummyTool)],
            },
        )
        with patch("agent.serializers.customs.fields.AgentRegistry.get_agent_class_by_type", return_value=agent_class):
            yield

    def test_settings_are_validated_and_stored_by_tool_name(self):
        serializer = get_map_model_serializer({"config": {"dummy": {"value_1": "Alice", "value_2": 25}}})

        serializer.is_valid(raise_exception=True)

        assert serializer.validated_data["config"] == {"dummy": {"value_1": "Alice", "value_2": 25}}

    def test_errors_are_keyed_by_tool_name(self):
        serializer = get_map_model_serializer({"config": {"dummy": {"value_1": "Missing number"}}})

        assert not serializer.is_valid()
        assert list(serializer.errors["config"]["dummy"]) == ["value_2"]

    def test_a_configurable_tool_left_out_is_validated_as_empty(self):
        serializer = get_map_model_serializer({"config": {}})

        assert not serializer.is_valid()
        assert set(serializer.errors["config"]["dummy"]) == {"value_1", "value_2"}

    @pytest.mark.parametrize("name", ["plain", "missing"])
    def test_a_tool_that_is_not_configurable_on_the_agent_is_rejected(self, name):
        serializer = get_map_model_serializer({"config": {"dummy": {"value_1": "a", "value_2": 1}, name: {}}})

        assert not serializer.is_valid()
        assert f"non-configurable tools: {name}" in str(serializer.errors["config"])

    @pytest.mark.parametrize("settings", [None, "proxy", ["a"]])
    def test_settings_that_are_not_an_object_are_an_error_of_that_tool(self, settings):
        serializer = get_map_model_serializer({"config": {"dummy": settings}})

        assert not serializer.is_valid()
        assert serializer.errors["config"]["dummy"] == ["Expected the tool's settings as an object."]

    def test_a_list_is_rejected(self):
        serializer = get_map_model_serializer({"config": [{"value_1": "a", "value_2": 1}]})

        assert not serializer.is_valid()
        assert "keyed by tool name" in str(serializer.errors["config"])
