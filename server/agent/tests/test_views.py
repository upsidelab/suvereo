from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from enthusiast_common.config import FunctionToolConfig
from enthusiast_common.tools import BaseFunctionTool
from enthusiast_common.utils import RequiredFieldsModel
from model_bakery import baker
from pydantic import Field
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import assign_dataset_role, set_application_admin
from account.models import User
from agent.models import Conversation, Message
from agent.models.agent import Agent
from agent.models.agentic_execution import AgenticExecution
from catalog.models import DataSet

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return baker.make(User, is_staff=False)


@pytest.fixture
def dataset(user):
    dataset = baker.make(DataSet)
    assign_dataset_role(user, dataset, "viewer")
    return dataset


@pytest.fixture
def agent(dataset):
    return baker.make(Agent, deleted_at=None, dataset=dataset)


@pytest.fixture
def deleted_agent(dataset):
    return baker.make(Agent, deleted_at=timezone.now(), dataset=dataset)


@pytest.fixture
def conversation(user, agent, dataset):
    return baker.make(Conversation, user=user, agent=agent, data_set=dataset)


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class ToolArgs(RequiredFieldsModel):
    required_test: str = Field(description="description", title="title")
    optional_test: str = Field(description="description", title="title", default="default")


class DummyTool(BaseFunctionTool):
    CONFIGURATION_ARGS = ToolArgs


class AgentArgs(RequiredFieldsModel):
    required_test: str = Field(description="description", title="title")
    optional_test: str = Field(description="description", title="title", default="default")


class PromptInput(RequiredFieldsModel):
    required_test: str = Field(description="description", title="title")
    optional_test: str = Field(description="description", title="title", default="default")


class PromptExtension(RequiredFieldsModel):
    required_test: str = Field(description="description", title="title")
    optional_test: str = Field(description="description", title="title", default="default")


class DummyAgentBase:
    AGENT_ARGS = AgentArgs
    PROMPT_INPUT = PromptInput
    PROMPT_EXTENSION = PromptExtension
    TOOLS = [FunctionToolConfig(tool_class=DummyTool), FunctionToolConfig(tool_class=DummyTool)]
    FILE_UPLOAD = False


class DummyAgent1(DummyAgentBase):
    AGENT_KEY = "agent_1"
    NAME = "dummy agent 1"

class DummyAgent2(DummyAgentBase):
    AGENT_KEY = "agent_2"
    NAME = "dummy agent 2"

AGENT_CLASSES = [DummyAgent1, DummyAgent2]


@pytest.fixture(autouse=True)
def django_settings(settings):
    settings.AVAILABLE_AGENTS = ['agent_path_1.Agent1', 'agent_path_2.Agent2']


@pytest.fixture
def config():
    return {
        "agent_args": {
            "required_test": "required_test",
            "optional_test": "optional_test",
        },
        "prompt_input": {
            "required_test": "required_test",
            "optional_test": "optional_test",
        },
        "prompt_extension": {
            "required_test": "required_test",
            "optional_test": "optional_test",
        },
        "tools": [
            {"required_test": "required_test", "optional_test": "optional_test"},
            {"required_test": "required_test", "optional_test": "optional_test"},
        ],
    }


class TestAgentTypesView:
    def test_get_agent_types_returns_200(self, api_client):
        url = reverse("agent-types")
        with patch("agent.views.AgentRegistry.get_plugin_classes", return_value=AGENT_CLASSES):
            response = api_client.get(url)

            assert response.status_code == status.HTTP_200_OK
            assert len(response.data["choices"]) == 2
            assert response.data["choices"][0]["key"] == "agent_1"
            assert response.data["choices"][1]["key"] == "agent_2"
            assert len(response.data["choices"][0]["tools"]) == 2
            assert len(response.data["choices"][1]["tools"]) == 2
            assert list(response.data["choices"][0]["tools"][0].keys()) == ["required_test", "optional_test"]

    def test_get_agent_types_returns_401(self):
        response = APIClient().get(reverse("agent-types"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAgentView:
    @pytest.fixture
    def url(self):
        return reverse("agents")

    @pytest.fixture
    def dataset_instance(self):
        return baker.make(DataSet)

    def test_get_empty_list(self, api_client, url, dataset_instance):
        response = api_client.get(f"{url}?dataset={dataset_instance.pk}")

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_get_multiple_agents(self, api_client, url, dataset_instance):
        config_1 = baker.make(Agent, name="cfg1", config={"a": 1}, dataset=dataset_instance)
        config_2 = baker.make(Agent, name="cfg2", config={"b": 2}, dataset=dataset_instance)

        response = api_client.get(f"{url}?dataset={dataset_instance.pk}")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        ids = {item["id"] for item in response.data}
        assert config_1.id in ids
        assert config_2.id in ids

    def test_get_returns_ordered_by_created_at(self, api_client, url, dataset_instance):
        older = baker.make(Agent, name="older", dataset=dataset_instance)
        newer = baker.make(Agent, name="newer", dataset=dataset_instance)

        response = api_client.get(f"{url}?dataset={dataset_instance.pk}")

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]["id"] == older.id
        assert response.data[1]["id"] == newer.id

    def test_get_returns_corrupted_agents_to_admin(self, user, api_client, url, dataset_instance):
        set_application_admin(user, True)
        agent_1 = baker.make(Agent, dataset=dataset_instance)
        agent_2 = baker.make(Agent, dataset=dataset_instance, corrupted=True)

        response = api_client.get(f"{url}?dataset={dataset_instance.pk}")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        ids = {item["id"] for item in response.data}
        assert agent_1.id in ids
        assert agent_2.id in ids

    def test_get_returns_corrupted_agents_to_dataset_editor(self, user, api_client, url, dataset_instance):
        assign_dataset_role(user, dataset_instance, "editor")
        agent_1 = baker.make(Agent, dataset=dataset_instance)
        agent_2 = baker.make(Agent, dataset=dataset_instance, corrupted=True)

        response = api_client.get(f"{url}?dataset={dataset_instance.pk}")

        assert response.status_code == status.HTTP_200_OK
        ids = {item["id"] for item in response.data}
        assert agent_1.id in ids
        assert agent_2.id in ids

    def test_editor_of_other_dataset_does_not_see_corrupted_agents_here(self, user, api_client, url, dataset_instance):
        other_dataset = baker.make(DataSet)
        assign_dataset_role(user, other_dataset, "editor")
        agent_1 = baker.make(Agent, dataset=dataset_instance)
        agent_2 = baker.make(Agent, dataset=dataset_instance, corrupted=True)

        response = api_client.get(f"{url}?dataset={dataset_instance.pk}")

        assert response.status_code == status.HTTP_200_OK
        ids = {item["id"] for item in response.data}
        assert agent_1.id in ids
        assert agent_2.id not in ids

    def test_editor_can_create_agent_on_their_dataset(self, user, api_client, url, dataset_instance, config):
        assign_dataset_role(user, dataset_instance, "editor")
        payload = {
            "name": "editor-made",
            "description": "description",
            "config": config,
            "dataset": dataset_instance.id,
            "agent_type": "agent_1",
        }

        with patch("agent.serializers.customs.fields.AgentRegistry.get_plugin_classes", return_value=AGENT_CLASSES):
            response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED

    def test_editor_cannot_create_agent_on_another_dataset(self, user, api_client, url, dataset_instance, config):
        other_dataset = baker.make(DataSet)
        assign_dataset_role(user, other_dataset, "editor")
        payload = {
            "name": "not-allowed",
            "description": "description",
            "config": config,
            "dataset": dataset_instance.id,
            "agent_type": "agent_1",
        }

        with patch("agent.serializers.customs.fields.AgentRegistry.get_plugin_classes", return_value=AGENT_CLASSES):
            response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_create_agent(self, user, api_client, url, dataset_instance, config):
        assign_dataset_role(user, dataset_instance, "viewer")
        payload = {
            "name": "not-allowed",
            "description": "description",
            "config": config,
            "dataset": dataset_instance.id,
            "agent_type": "agent_1",
        }
        with patch("agent.serializers.customs.fields.AgentRegistry.get_plugin_classes", return_value=AGENT_CLASSES):
            response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_group_member_can_create_agent_via_group_grant(self, api_client, user, dataset_instance, config, url):
        from django.contrib.auth.models import Group

        group = Group.objects.create(name="Marketing")
        assign_dataset_role(group, dataset_instance, "editor")
        user.groups.add(group)
        payload = {
            "name": "group-made",
            "description": "description",
            "config": config,
            "dataset": dataset_instance.id,
            "agent_type": "agent_1",
        }

        with patch("agent.serializers.customs.fields.AgentRegistry.get_plugin_classes", return_value=AGENT_CLASSES):
            response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED

    def test_get_filter_out_corrupted_agents_to_user(self, api_client, url, dataset_instance):
        agent_1 = baker.make(Agent, dataset=dataset_instance)
        agent_2 = baker.make(Agent, dataset=dataset_instance, corrupted=True)

        response = api_client.get(f"{url}?dataset={dataset_instance.pk}")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        ids = {item["id"] for item in response.data}
        assert agent_1.id in ids
        assert agent_2.id not in ids

    def test_dataset_not_found(self, api_client, url):
        response = api_client.get(f"{url}?dataset=9999")

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_get_with_non_numeric_dataset_param_returns_400(self, api_client, url):
        response = api_client.get(f"{url}?dataset=abc")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_post_creates_agent(self, admin_api_client, url, config):
        dataset = baker.make(DataSet)
        config = {
            "agent_args": {
                "required_test": "required_test",
            },
            "prompt_input": {
                "required_test": "required_test",
            },
            "prompt_extension": {
                "required_test": "required_test",
            },
            "tools": [
                {
                    "required_test": "required_test",
                },
                {
                    "required_test": "required_test",
                },
            ],
        }
        payload = {
            "name": "name",
            "description": "description",
            "config": config,
            "dataset": dataset.id,
            "agent_type": "agent_1",
        }

        with patch("agent.serializers.customs.fields.AgentRegistry.get_plugin_classes", return_value=AGENT_CLASSES):
            response = admin_api_client.post(url, payload, format="json")

            assert response.status_code == status.HTTP_201_CREATED
            created = Agent.objects.get(pk=response.data["id"])
            assert created.name == "name"

    def test_post_creates_agent_optional_fields_saved(self, admin_api_client, url, config):
        dataset = baker.make(DataSet)
        config = {
            "agent_args": {
                "required_test": "required_test",
                "optional_test": "optional_test",
            },
            "prompt_input": {
                "required_test": "required_test",
                "optional_test": "optional_test",
            },
            "prompt_extension": {
                "required_test": "required_test",
                "optional_test": "optional_test",
            },
            "tools": [
                {"required_test": "required_test", "optional_test": "optional_test"},
                {"required_test": "required_test", "optional_test": "optional_test"},
            ],
        }
        payload = {
            "name": "name",
            "description": "description",
            "config": config,
            "dataset": dataset.id,
            "agent_type": "agent_1",
        }

        with patch("agent.serializers.customs.fields.AgentRegistry.get_plugin_classes", return_value=AGENT_CLASSES):
            response = admin_api_client.post(url, payload, format="json")

            assert response.status_code == status.HTTP_201_CREATED
            created = Agent.objects.get(pk=response.data["id"])
            assert created.name == "name"
            assert created.config["tools"][0].get("optional_test") == "optional_test"
            assert created.config["tools"][1].get("optional_test") == "optional_test"
            assert created.config["agent_args"].get("optional_test") == "optional_test"
            assert created.config["prompt_input"].get("optional_test") == "optional_test"
            assert created.config["prompt_extension"].get("optional_test") == "optional_test"

    def test_post_creates_agent_do_not_save_empty_field(self, admin_api_client, url, config):
        dataset = baker.make(DataSet)
        config = {
            "agent_args": {
                "required_test": "required_test",
            },
            "prompt_input": {
                "required_test": "required_test",
            },
            "prompt_extension": {
                "required_test": "required_test",
            },
            "tools": [{"required_test": "required_test"}, {"required_test": "required_test"}],
        }
        payload = {
            "name": "name",
            "description": "description",
            "config": config,
            "dataset": dataset.id,
            "agent_type": "agent_1",
        }

        class NoArgsDummyTool(BaseFunctionTool):
            CONFIGURATION_ARGS = None

        class NoArgsDummyAgent:
            AGENT_ARGS = None
            PROMPT_INPUT = PromptInput
            PROMPT_EXTENSION = PromptExtension
            TOOLS = [FunctionToolConfig(tool_class=NoArgsDummyTool), FunctionToolConfig(tool_class=DummyTool)]
            FILE_UPLOAD = False

        with patch(
            "agent.serializers.customs.fields.AgentRegistry.get_agent_class_by_type", return_value=NoArgsDummyAgent
        ):
            response = admin_api_client.post(url, payload, format="json")

            assert response.status_code == status.HTTP_201_CREATED
            created = Agent.objects.get(pk=response.data["id"])
            assert created.name == "name"
            assert created.config["agent_args"] == {}
            assert created.config["tools"][0] == {}
            assert created.config["tools"][1] == {"required_test": "required_test", "optional_test": "default"}

    def test_post_without_manage_agents_permission_returns_403(self, api_client, url, dataset_instance, config):
        payload = {
            "name": "nope",
            "description": "description",
            "config": config,
            "dataset": dataset_instance.id,
            "agent_type": "agent_1",
        }

        with patch("agent.serializers.customs.fields.AgentRegistry.get_plugin_classes", return_value=AGENT_CLASSES):
            response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAgentDetailsView:
    @pytest.fixture
    def agent_instance(self, config):
        return baker.make(Agent, name="cfg1", config=config)

    @pytest.fixture
    def url(self, agent_instance):
        return reverse("agent-details", kwargs={"pk": agent_instance.pk})

    def test_get_existing_agent(self, api_client, agent_instance, url):
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == agent_instance.name
        assert response.data["config"]

    def test_get_nonexistent_agent_returns_404(self, api_client):
        url = reverse("agent-details", kwargs={"pk": 9999})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_editor_of_this_dataset_can_update_agent(self, user, agent_instance, url, config):
        assign_dataset_role(user, agent_instance.dataset, "editor")
        client = APIClient()
        client.force_authenticate(user=user)
        updated_config = config
        payload = {
            "name": "updated-by-editor",
            "description": "description",
            "config": updated_config,
            "dataset": agent_instance.dataset.id,
            "agent_type": "agent_1",
        }
        with patch("agent.serializers.customs.fields.AgentRegistry.get_plugin_classes", return_value=AGENT_CLASSES):
            response = client.put(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK

    def test_editor_of_another_dataset_cannot_update_agent(self, agent_instance, url, config):
        other_dataset = baker.make(DataSet)
        user = baker.make(User)
        assign_dataset_role(user, other_dataset, "editor")
        client = APIClient()
        client.force_authenticate(user=user)
        payload = {
            "name": "not-allowed",
            "description": "description",
            "config": config,
            "dataset": agent_instance.dataset.id,
            "agent_type": "agent_1",
        }
        with patch("agent.serializers.customs.fields.AgentRegistry.get_plugin_classes", return_value=AGENT_CLASSES):
            response = client.put(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_editor_cannot_reassign_agent_to_a_dataset_they_have_no_rights_to(self, agent_instance, url, config):
        original_dataset_id = agent_instance.dataset_id
        user = baker.make(User)
        assign_dataset_role(user, agent_instance.dataset, "editor")
        other_dataset = baker.make(DataSet)
        client = APIClient()
        client.force_authenticate(user=user)
        payload = {
            "name": "not-allowed",
            "description": "description",
            "config": config,
            "dataset": other_dataset.id,
            "agent_type": "agent_1",
        }
        with patch("agent.serializers.customs.fields.AgentRegistry.get_plugin_classes", return_value=AGENT_CLASSES):
            response = client.put(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        agent_instance.refresh_from_db()
        assert agent_instance.dataset_id == original_dataset_id

    def test_viewer_cannot_update_agent(self, agent_instance, url, config):
        user = baker.make(User)
        assign_dataset_role(user, agent_instance.dataset, "viewer")
        client = APIClient()
        client.force_authenticate(user=user)
        payload = {
            "name": "not-allowed",
            "description": "description",
            "config": config,
            "dataset": agent_instance.dataset.id,
            "agent_type": "agent_1",
        }
        with patch("agent.serializers.customs.fields.AgentRegistry.get_plugin_classes", return_value=AGENT_CLASSES):
            response = client.put(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_delete_agent(self, agent_instance, url):
        user = baker.make(User)
        assign_dataset_role(user, agent_instance.dataset, "viewer")
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_editor_of_this_dataset_can_delete_agent(self, agent_instance, url):
        user = baker.make(User)
        assign_dataset_role(user, agent_instance.dataset, "editor")
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_put_updates_agent(self, admin_api_client, agent_instance, url, config):
        dataset = baker.make(DataSet)
        updated_config = {
            "agent_args": {
                "required_test": "required_updated",
                "optional_test": "optional_updated",
            },
            "prompt_input": {
                "required_test": "required_updated",
                "optional_test": "optional_updated",
            },
            "prompt_extension": {
                "required_test": "required_updated",
                "optional_test": "optional_updated",
            },
            "tools": [
                {"required_test": "required_upated", "optional_test": "optional_updated"},
                {"required_test": "required_updated", "optional_test": "optional_updated"},
            ],
        }
        payload = {
            "name": "updated",
            "description": "description",
            "config": updated_config,
            "dataset": dataset.id,
            "agent_type": "agent_1",
        }
        with patch("agent.serializers.customs.fields.AgentRegistry.get_plugin_classes", return_value=AGENT_CLASSES):
            response = admin_api_client.put(url, payload, format="json")

            assert response.status_code == status.HTTP_200_OK
            agent_instance.refresh_from_db()
            assert agent_instance.name == "updated"
            assert agent_instance.config == updated_config

    def test_put_removes_corrupted_flag_for_correct_data(self, admin_api_client, url, config):
        dataset = baker.make(DataSet)
        agent_instance = baker.make(Agent, corrupted=True, deleted_at=None, dataset=dataset)
        url = reverse("agent-details", kwargs={"pk": agent_instance.pk})
        updated_config = {
            "agent_args": {
                "required_test": "required_updated",
                "optional_test": "optional_updated",
            },
            "prompt_input": {
                "required_test": "required_updated",
                "optional_test": "optional_updated",
            },
            "prompt_extension": {
                "required_test": "required_updated",
                "optional_test": "optional_updated",
            },
            "tools": [
                {"required_test": "required_upated", "optional_test": "optional_updated"},
                {"required_test": "required_updated", "optional_test": "optional_updated"},
            ],
        }
        payload = {
            "name": "updated",
            "description": "description",
            "config": updated_config,
            "dataset": dataset.id,
            "agent_type": "agent_1",
        }
        with patch("agent.serializers.customs.fields.AgentRegistry.get_plugin_classes", return_value=AGENT_CLASSES):
            response = admin_api_client.put(url, payload, format="json")

            assert response.status_code == status.HTTP_200_OK
            agent_instance.refresh_from_db()
            assert agent_instance.corrupted is False

    def test_put_nonexistent_returns_404(self, admin_api_client):
        url = reverse("agent-details", kwargs={"pk": 9999})
        payload = {"name": "anything", "config": {"x": "y"}}

        response = admin_api_client.put(url, payload, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_put_invalid_payload_returns_400(self, admin_api_client, url):
        payload = {"name": ""}

        response = admin_api_client.put(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "config" in response.data

    def test_delete_existing_agent(self, admin_api_client, agent_instance, url):
        response = admin_api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        agent_instance = Agent.all_objects.get(pk=agent_instance.pk)
        assert agent_instance.deleted_at is not None

    def test_delete_nonexistent_agent_returns_404(self, admin_api_client, url):
        url = reverse("agent-details", kwargs={"pk": 9999})
        response = admin_api_client.delete(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_put_without_manage_agents_permission_returns_403(self, api_client, url):
        response = api_client.put(url, {"name": "nope"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_put_with_incomplete_payload_and_no_dataset_permission_returns_403_not_500(self, agent_instance, url):
        user = baker.make(User)
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.put(url, {"name": "nope"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_without_manage_agents_permission_returns_403(self, api_client, agent_instance, url):
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Agent.objects.filter(pk=agent_instance.pk).exists()

    def test_get_does_not_require_manage_agents_permission(self, api_client, agent_instance, url):
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK


class TestMessageFeedbackView:
    @pytest.fixture
    def message(self, conversation):
        return baker.make(Message, conversation=conversation, type=Message.MessageType.AI)

    def test_conversation_owner_can_leave_feedback(self, api_client, message):
        url = f"/api/messages/{message.id}/feedback/"

        response = api_client.patch(url, {"rating": 5, "feedback": "great answer"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        message.refresh_from_db()
        assert message.rating == 5
        assert message.feedback == "great answer"

    def test_other_user_cannot_leave_feedback(self, message):
        other_user = baker.make(User)
        client = APIClient()
        client.force_authenticate(user=other_user)
        url = f"/api/messages/{message.id}/feedback/"

        response = client.patch(url, {"rating": 1, "feedback": "sneaky"}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        message.refresh_from_db()
        assert message.rating is None


class TestConversationView:
    @pytest.fixture
    def url(self, conversation):
        return reverse("conversation-details", kwargs={"conversation_id": conversation.id})

    def test_valid_post_returns_202(self, api_client, url, conversation):
        payload = {
            "data_set_id": conversation.data_set.id,
            "question_message": "Hello?",
            "streaming": True,
        }
        with (
            patch(
                "agent.views.respond_to_user_message_task.apply_async",
                return_value=type("obj", (), {"id": "fake-task-id"}),
            ) as mock_task,
            patch("agent.views.LanguageModelRegistry.provider_for_dataset") as mock_provider,
        ):
            mock_provider.return_value = type("obj", (), {"STREAMING_AVAILABLE": True})
            response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data["task_id"] == "fake-task-id"
        assert response.data["streaming"] is True
        mock_task.assert_called_once()

    def test_non_streaming_provider_disables_streaming_in_task(self, api_client, url, conversation):
        payload = {
            "data_set_id": conversation.data_set.id,
            "question_message": "Hello?",
            "streaming": True,
        }
        with (
            patch(
                "agent.views.respond_to_user_message_task.apply_async",
                return_value=type("obj", (), {"id": "fake-task-id"}),
            ) as mock_task,
            patch("agent.views.LanguageModelRegistry.provider_for_dataset") as mock_provider,
        ):
            mock_provider.return_value = type("obj", (), {"STREAMING_AVAILABLE": False})
            response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data["streaming"] is False
        assert mock_task.call_args.kwargs["kwargs"]["streaming"] is False

    def test_invalid_payload_returns_400(self, api_client, url):
        payload = {"data_set_id": None}
        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "question_message" in response.data

    def test_agent_soft_deleted_returns_400(self, api_client, conversation, url):
        conversation.agent.deleted_at = timezone.now()
        conversation.agent.save()

        payload = {
            "data_set_id": conversation.data_set.id,
            "question_message": "Hello?",
            "streaming": False,
        }
        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Conversation locked."

    def test_execution_conversation_post_returns_400(self, api_client, conversation, url):
        baker.make(AgenticExecution, agent=conversation.agent, conversation=conversation, input={})

        payload = {
            "data_set_id": conversation.data_set.id,
            "question_message": "Hello?",
            "streaming": False,
        }
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Conversation locked."

    def test_conversation_not_found_returns_404(self, api_client):
        url = reverse("conversation-details", kwargs={"conversation_id": 99999})
        payload = {
            "data_set_id": 1,
            "question_message": "Hello?",
            "streaming": False,
        }
        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_can_post_to_any_conversation(self, admin_api_client, url):
        dataset = baker.make(DataSet)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        conversation = baker.make(Conversation, agent=agent)
        url = reverse("conversation-details", kwargs={"conversation_id": conversation.id})
        payload = {"data_set_id": dataset.id, "question_message": "How are you?", "streaming": False}

        with (
            patch(
                "agent.views.respond_to_user_message_task.apply_async",
                return_value=type("obj", (), {"id": "fake-task-id"}),
            ) as mock_task,
            patch("agent.views.LanguageModelRegistry.provider_for_dataset") as mock_provider,
        ):
            mock_provider.return_value = type("obj", (), {"STREAMING_AVAILABLE": True})
            response = admin_api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED
        mock_task.assert_called_once()

    def test_user_can_not_post_to_conversation_with_no_dataset_access(self, api_client, url):
        dataset = baker.make(DataSet)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        conversation = baker.make(Conversation, agent=agent)
        url = reverse("conversation-details", kwargs={"conversation_id": conversation.id})
        payload = {"data_set_id": dataset.id, "question_message": "How are you?", "streaming": False}

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestConversationListView:
    @pytest.fixture
    def url(self):
        return reverse("conversation-list")

    def test_create_conversation_success(self, api_client, agent, url):
        payload = {"agent_id": agent.id}

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["agent"]["id"] == agent.id

    def test_create_conversation_invalid_payload(self, api_client, url):
        payload = {"wrong_field": 123}

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "agent_id" in response.data

    def test_create_conversation_with_deleted_agent(self, api_client, deleted_agent, url):
        payload = {"agent_id": deleted_agent.id}

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_conversation_throws_on_no_access_to_dataset(self, api_client, url):
        dataset = baker.make(DataSet)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        payload = {"agent_id": agent.id}

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_create_conversation_with_any_dataset(self, admin_api_client, url):
        dataset = baker.make(DataSet)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        payload = {"agent_id": agent.id}

        response = admin_api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["agent"]["id"] == agent.id

    def test_list_conversations_returns_all_user_conversations(self, api_client, user, dataset, url):
        agent1 = baker.make(Agent, deleted_at=None, dataset=dataset)
        agent2 = baker.make(Agent, deleted_at=None, dataset=dataset)
        conversation1 = baker.make(Conversation, user=user, agent=agent1, data_set=dataset)
        conversation2 = baker.make(Conversation, user=user, agent=agent2, data_set=dataset)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2
        conversation_ids = [conv["id"] for conv in response.data["results"]]
        assert conversation1.id in conversation_ids
        assert conversation2.id in conversation_ids

    def test_list_conversations_filters_by_agent_id(self, api_client, user, dataset, url):
        agent1 = baker.make(Agent, deleted_at=None, dataset=dataset)
        agent2 = baker.make(Agent, deleted_at=None, dataset=dataset)
        conversation1 = baker.make(Conversation, user=user, agent=agent1, data_set=dataset)
        baker.make(Conversation, user=user, agent=agent2, data_set=dataset)

        response = api_client.get(url, {"agent_id": agent1.id})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["id"] == conversation1.id
        assert response.data["results"][0]["agent"]["id"] == agent1.id

    def test_list_conversations_with_agent_id_returns_empty_when_no_matches(self, api_client, user, dataset, url):
        agent1 = baker.make(Agent, deleted_at=None, dataset=dataset)
        agent2 = baker.make(Agent, deleted_at=None, dataset=dataset)
        baker.make(Conversation, user=user, agent=agent1, data_set=dataset)

        response = api_client.get(url, {"agent_id": agent2.id})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

    def test_list_conversations_with_agent_id_only_returns_user_conversations(self, api_client, user, dataset, url):
        other_user = baker.make(User)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        user_conversation = baker.make(Conversation, user=user, agent=agent, data_set=dataset)
        baker.make(Conversation, user=other_user, agent=agent, data_set=dataset)

        response = api_client.get(url, {"agent_id": agent.id})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["id"] == user_conversation.id

    def test_list_conversations_filters_by_data_set_id(self, api_client, user, url):
        dataset1 = baker.make(DataSet)
        dataset2 = baker.make(DataSet)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset1)
        conversation1 = baker.make(Conversation, user=user, agent=agent, data_set=dataset1)
        baker.make(Conversation, user=user, agent=agent, data_set=dataset2)

        response = api_client.get(url, {"data_set_id": dataset1.id})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["id"] == conversation1.id

    def test_list_conversations_filters_by_data_set_id_and_agent_id(self, api_client, user, url):
        dataset1 = baker.make(DataSet)
        dataset2 = baker.make(DataSet)
        agent1 = baker.make(Agent, deleted_at=None, dataset=dataset1)
        agent2 = baker.make(Agent, deleted_at=None, dataset=dataset1)
        conversation1 = baker.make(Conversation, user=user, agent=agent1, data_set=dataset1)
        baker.make(Conversation, user=user, agent=agent2, data_set=dataset1)
        baker.make(Conversation, user=user, agent=agent1, data_set=dataset2)

        response = api_client.get(url, {"data_set_id": dataset1.id, "agent_id": agent1.id})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["id"] == conversation1.id
        assert response.data["results"][0]["agent"]["id"] == agent1.id

    def test_list_conversations_with_data_set_id_returns_empty_when_no_matches(self, api_client, user, url):
        dataset1 = baker.make(DataSet)
        dataset2 = baker.make(DataSet)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset1)
        baker.make(Conversation, user=user, agent=agent, data_set=dataset1)

        response = api_client.get(url, {"data_set_id": dataset2.id})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

    def test_list_conversations_with_data_set_id_only_returns_user_conversations(self, api_client, user, url):
        other_user = baker.make(User)
        dataset = baker.make(DataSet)
        other_dataset = baker.make(DataSet)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        user_conversation = baker.make(Conversation, user=user, agent=agent, data_set=dataset)
        baker.make(Conversation, user=other_user, agent=agent, data_set=other_dataset)

        response = api_client.get(url, {"data_set_id": dataset.id})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["id"] == user_conversation.id

    def test_execution_conversations_are_excluded_from_list(self, api_client, user, dataset, url):
        linked_agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        regular_conversation = baker.make(Conversation, user=user, agent=linked_agent, data_set=dataset)
        execution_conversation = baker.make(Conversation, user=user, agent=linked_agent, data_set=dataset)
        baker.make(AgenticExecution, agent=linked_agent, conversation=execution_conversation, input={})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        conversation_ids = [conv["id"] for conv in response.data["results"]]
        assert regular_conversation.id in conversation_ids
        assert execution_conversation.id not in conversation_ids

    def test_execution_conversation_is_accessible_via_detail_endpoint(self, api_client, user, dataset, url):
        linked_agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        execution_conversation = baker.make(Conversation, user=user, agent=linked_agent, data_set=dataset)
        baker.make(AgenticExecution, agent=linked_agent, conversation=execution_conversation, input={})

        response = api_client.get(reverse("conversation-details", kwargs={"conversation_id": execution_conversation.id}))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == execution_conversation.id
