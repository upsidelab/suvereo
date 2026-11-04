from drf_yasg import openapi
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError
from rest_framework import serializers
from rest_framework.exceptions import APIException
from utils.serializers import BasePydanticModelField

from agent.core.agents.configurable_tools import ConfigurableTools
from agent.core.registries.agents.agent_registry import AgentRegistry


class PydanticModelField(BasePydanticModelField):
    def __init__(self, *, agent_field_name: str, **kwargs):
        self.agent_field_name = agent_field_name
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        agent_type = self.context.get("agent_type")
        if not agent_type:
            raise AssertionError("Missing 'agent_type' in field context")

        try:
            class_obj = AgentRegistry().get_agent_class_by_type(agent_type)
        except Exception as e:
            raise APIException(f"Error loading agent: {str(e)}")

        try:
            schema = getattr(class_obj, self.agent_field_name)
        except KeyError:
            raise serializers.ValidationError(f"Unknown schema for field: {self.agent_field_name}")

        if not schema:
            return {}

        try:
            return schema(**data).model_dump()
        except PydanticValidationError as e:
            raise serializers.ValidationError(self._format_pydantic_errors(e))

    def to_representation(self, value):
        if isinstance(value, BaseModel):
            return value.model_dump()
        return value

    class Meta:
        swagger_schema_fields = {"type": openapi.TYPE_OBJECT}


class PydanticModelToolMapField(BasePydanticModelField):
    def to_internal_value(self, data):
        agent_type = self.context.get("agent_type")
        if not agent_type:
            raise AssertionError("Missing 'agent_type' in field context")

        try:
            tools = ConfigurableTools.for_agent(AgentRegistry().get_agent_class_by_type(agent_type))
        except Exception as e:
            raise serializers.ValidationError(f"Error loading agent: {str(e)}") from e

        if not isinstance(data, dict):
            raise serializers.ValidationError("Expected tool configurations keyed by tool name.")
        if unknown := sorted(set(data) - set(tools)):
            raise serializers.ValidationError(f"Unknown or non-configurable tools: {', '.join(unknown)}.")

        validated, errors = {}, {}
        for name, tool_class in tools.items():
            settings = data.get(name, {})
            if not isinstance(settings, dict):
                errors[name] = ["Expected the tool's settings as an object."]
                continue
            try:
                validated[name] = tool_class.CONFIGURATION_ARGS(**settings).model_dump()
            except PydanticValidationError as e:
                errors[name] = self._format_pydantic_errors(e)

        if errors:
            raise serializers.ValidationError(errors)

        return validated

    def to_representation(self, value):
        return value

    class Meta:
        swagger_schema_fields = {"type": openapi.TYPE_OBJECT}
