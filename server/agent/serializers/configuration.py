from rest_framework import serializers
from rest_framework.exceptions import APIException
from utils.functions import get_model_descriptor_from_class_field
from utils.serializers import ExtraArgDetailSerializer, ParentDataContextSerializerMixin

from agent.core.registries.agents.agent_registry import AgentRegistry
from agent.models import Agent
from agent.serializers.customs.fields import PydanticModelField, PydanticModelToolListField
from catalog.models import DataSet


def agent_class_for(agent: Agent):
    try:
        return AgentRegistry().get_agent_class_by_type(agent.agent_type)
    except Exception:
        return None


def agent_type_display_name(agent: Agent) -> str:
    agent_class = agent_class_for(agent)
    return getattr(agent_class, "NAME", None) or agent.agent_type


def agent_type_config_schema(agent_class) -> dict:
    return {
        "agent_args": get_model_descriptor_from_class_field(agent_class, "AGENT_ARGS"),
        "prompt_input": get_model_descriptor_from_class_field(agent_class, "PROMPT_INPUT"),
        "prompt_extension": get_model_descriptor_from_class_field(agent_class, "PROMPT_EXTENSION"),
        "tools": [
            get_model_descriptor_from_class_field(tool_config.tool_class, "CONFIGURATION_ARGS")
            for tool_config in getattr(agent_class, "TOOLS", None) or []
        ],
    }


class AgentChoiceSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    agent_args = serializers.DictField(child=ExtraArgDetailSerializer(), allow_empty=True)
    prompt_input = serializers.DictField(child=ExtraArgDetailSerializer(), allow_empty=True)
    prompt_extension = serializers.DictField(child=ExtraArgDetailSerializer(), allow_empty=True)
    tools = serializers.ListField(child=serializers.DictField(child=ExtraArgDetailSerializer()), allow_empty=True)


class AvailableAgentsResponseSerializer(serializers.Serializer):
    choices = serializers.ListField(child=AgentChoiceSerializer())


class AgentConfigSerializer(ParentDataContextSerializerMixin, serializers.Serializer):
    context_keys_to_propagate = ["agent_type"]

    agent_args = PydanticModelField(agent_field_name="AGENT_ARGS")
    prompt_input = PydanticModelField(agent_field_name="PROMPT_INPUT")
    prompt_extension = PydanticModelField(agent_field_name="PROMPT_EXTENSION")
    tools = PydanticModelToolListField(agent_field_name="TOOLS", tool_field_name="CONFIGURATION_ARGS")


class AgentSerializer(ParentDataContextSerializerMixin, serializers.ModelSerializer):
    context_keys_to_propagate = ["agent_type"]

    config = AgentConfigSerializer()
    dataset = serializers.PrimaryKeyRelatedField(queryset=DataSet.objects.all())
    agent_type_name = serializers.SerializerMethodField()
    config_schema = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = [
            "id",
            "name",
            "description",
            "config",
            "config_schema",
            "dataset",
            "agent_type",
            "agent_type_name",
            "created_at",
            "updated_at",
            "file_upload",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "file_upload"]

    def get_fields(self):
        """Return the serializer fields, making `dataset` read-only once the agent exists."""
        fields = super().get_fields()
        if self.instance is not None:
            fields["dataset"] = serializers.PrimaryKeyRelatedField(read_only=True)
        return fields

    def get_agent_type_name(self, agent) -> str:
        return agent_type_display_name(agent)

    def get_config_schema(self, agent) -> dict:
        agent_class = agent_class_for(agent)
        return agent_type_config_schema(agent_class) if agent_class else {}

    def validate_name(self, name):
        data_set = self.instance.dataset if self.instance else self.initial_data.get("dataset")

        if Agent.objects.filter(dataset=data_set, name=name).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("An agent with this name already exists in this dataset.")

        return name

    def create(self, validated_data):
        agent_type = self.context.get("agent_type")
        if not agent_type:
            raise AssertionError("Missing 'agent_type' in field context")

        try:
            class_obj = AgentRegistry().get_agent_class_by_type(agent_type)
        except Exception as e:
            raise APIException(f"Error loading agent: {str(e)}")
        validated_data["file_upload"] = class_obj.FILE_UPLOAD
        return super().create(validated_data)

    def update(self, instance, validated_data):
        agent_type = self.context.get("agent_type")
        if not agent_type:
            raise AssertionError("Missing 'agent_type' in field context")

        try:
            class_obj = AgentRegistry().get_agent_class_by_type(agent_type)
        except Exception as e:
            raise APIException(f"Error loading agent: {str(e)}")

        validated_data["file_upload"] = class_obj.FILE_UPLOAD
        return super().update(instance, validated_data)


class AgentListSerializer(ParentDataContextSerializerMixin, serializers.ModelSerializer):
    context_keys_to_propagate = ["agent_type"]

    agent_type_name = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = [
            "id",
            "name",
            "description",
            "dataset",
            "agent_type",
            "agent_type_name",
            "created_at",
            "updated_at",
            "deleted_at",
            "corrupted",
        ]

    def get_agent_type_name(self, agent) -> str:
        return agent_type_display_name(agent)
