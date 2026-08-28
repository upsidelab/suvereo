from unittest.mock import patch

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone
from enthusiast_common.config import FunctionToolConfig
from enthusiast_common.tools import BaseFunctionTool
from enthusiast_common.utils import RequiredFieldsModel
from model_bakery import baker
from pydantic import Field
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.models import DatasetRole, DatasetUserRoleAssignment, User
from account.tests.helpers import grant
from agent.models import Conversation, Message
from agent.models.agent import Agent
from agent.models.agentic_execution import AgenticExecution
from catalog.models import DataSet

pytestmark = pytest.mark.django_db


def _permission(codename: str) -> Permission:
    app_label, name = codename.split(".")
    return Permission.objects.get(codename=name, content_type__app_label=app_label)


def _grant_dataset_permission(user, dataset, *codenames: str) -> DatasetRole:
    role = baker.make(DatasetRole)
    role.permissions.set([_permission(codename) for codename in codenames])
    baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)
    return role


@pytest.fixture
def user():
    return baker.make(User, is_superuser=False)


@pytest.fixture
def dataset():
    return baker.make(DataSet)


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
    def test_get_agent_types_returns_401(self):
        response = APIClient().get(reverse("agent-types"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_outsider_with_no_add_or_change_agent_anywhere_is_denied(self, api_client):
        url = reverse("agent-types")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_dataset_member_holding_only_add_agent_is_allowed(self, api_client, user):
        dataset = baker.make(DataSet)
        _grant_dataset_permission(user, dataset, PERMISSIONS.AGENT.ADD)
        url = reverse("agent-types")

        with patch("agent.views.AgentRegistry.get_plugin_classes", return_value=AGENT_CLASSES):
            response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_get_agent_types_returns_200(self, api_client, user):
        dataset = baker.make(DataSet)
        _grant_dataset_permission(user, dataset, PERMISSIONS.AGENT.ADD)
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


class TestAgentView:
    @pytest.fixture
    def url(self):
        return reverse("agents")

    @pytest.fixture
    def dataset_instance(self):
        return baker.make(DataSet)

    def test_get_outsider_gets_not_found(self, api_client, url, dataset_instance):
        response = api_client.get(f"{url}?dataset={dataset_instance.pk}")

        # Obscured as 404, not 403 - a non-member shouldn't be able to tell this dataset
        # apart from one that doesn't exist.
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_outsider_gets_identical_404_body_to_a_nonexistent_dataset(self, api_client, url, dataset_instance):
        # The two cases must be indistinguishable - not just the same status code, but the
        # same response body - or a non-member could tell them apart by comparing responses.
        existing_but_hidden = api_client.get(f"{url}?dataset={dataset_instance.pk}")
        nonexistent = api_client.get(f"{url}?dataset=9999")

        assert existing_but_hidden.data == {"detail": "No DataSet matches the given query."}
        assert existing_but_hidden.data == nonexistent.data

    def test_get_dataset_member_without_view_agent_gets_forbidden(self, api_client, user, url, dataset_instance):
        # A member of the dataset, but the role grants nothing agent-related.
        _grant_dataset_permission(user, dataset_instance)

        response = api_client.get(f"{url}?dataset={dataset_instance.pk}")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_empty_list(self, api_client, user, url, dataset_instance):
        _grant_dataset_permission(user, dataset_instance, PERMISSIONS.AGENT.VIEW)

        response = api_client.get(f"{url}?dataset={dataset_instance.pk}")

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_get_multiple_agents(self, api_client, user, url, dataset_instance):
        _grant_dataset_permission(user, dataset_instance, PERMISSIONS.AGENT.VIEW)
        config_1 = baker.make(Agent, name="cfg1", config={"a": 1}, dataset=dataset_instance)
        config_2 = baker.make(Agent, name="cfg2", config={"b": 2}, dataset=dataset_instance)

        response = api_client.get(f"{url}?dataset={dataset_instance.pk}")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        ids = {item["id"] for item in response.data}
        assert config_1.id in ids
        assert config_2.id in ids

    def test_get_returns_ordered_by_created_at(self, api_client, user, url, dataset_instance):
        _grant_dataset_permission(user, dataset_instance, PERMISSIONS.AGENT.VIEW)
        older = baker.make(Agent, name="older", dataset=dataset_instance)
        newer = baker.make(Agent, name="newer", dataset=dataset_instance)

        response = api_client.get(f"{url}?dataset={dataset_instance.pk}")

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]["id"] == older.id
        assert response.data[1]["id"] == newer.id

    def test_get_returns_corrupted_agents_to_admin(self, user, api_client, url, dataset_instance):
        user.is_superuser = True
        user.save()
        agent_1 = baker.make(Agent, dataset=dataset_instance)
        agent_2 = baker.make(Agent, dataset=dataset_instance, corrupted=True)

        response = api_client.get(f"{url}?dataset={dataset_instance.pk}")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        ids = {item["id"] for item in response.data}
        assert agent_1.id in ids
        assert agent_2.id in ids

    def test_get_filter_out_corrupted_agents_to_user(self, api_client, user, url, dataset_instance):
        _grant_dataset_permission(user, dataset_instance, PERMISSIONS.AGENT.VIEW)
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

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_post_outsider_gets_not_found(self, api_client, url):
        dataset = baker.make(DataSet)

        response = api_client.post(url, {"dataset": dataset.id}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_post_dataset_member_without_add_agent_gets_forbidden(self, api_client, user, url):
        dataset = baker.make(DataSet)
        _grant_dataset_permission(user, dataset)

        response = api_client.post(url, {"dataset": dataset.id}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_post_creates_agent(self, api_client, user, url, config):
        dataset = baker.make(DataSet)
        _grant_dataset_permission(user, dataset, PERMISSIONS.AGENT.ADD)
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
            response = api_client.post(url, payload, format="json")

            assert response.status_code == status.HTTP_201_CREATED
            created = Agent.objects.get(pk=response.data["id"])
            assert created.name == "name"

    def test_post_creates_agent_optional_fields_saved(self, api_client, user, url, config):
        dataset = baker.make(DataSet)
        _grant_dataset_permission(user, dataset, PERMISSIONS.AGENT.ADD)
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
            response = api_client.post(url, payload, format="json")

            assert response.status_code == status.HTTP_201_CREATED
            created = Agent.objects.get(pk=response.data["id"])
            assert created.name == "name"
            assert created.config["tools"][0].get("optional_test") == "optional_test"
            assert created.config["tools"][1].get("optional_test") == "optional_test"
            assert created.config["agent_args"].get("optional_test") == "optional_test"
            assert created.config["prompt_input"].get("optional_test") == "optional_test"
            assert created.config["prompt_extension"].get("optional_test") == "optional_test"

    def test_post_creates_agent_do_not_save_empty_field(self, api_client, user, url, config):
        dataset = baker.make(DataSet)
        _grant_dataset_permission(user, dataset, PERMISSIONS.AGENT.ADD)
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
            response = api_client.post(url, payload, format="json")

            assert response.status_code == status.HTTP_201_CREATED
            created = Agent.objects.get(pk=response.data["id"])
            assert created.name == "name"
            assert created.config["agent_args"] == {}
            assert created.config["tools"][0] == {}
            assert created.config["tools"][1] == {"required_test": "required_test", "optional_test": "default"}


class TestAgentDetailsView:
    @pytest.fixture
    def agent_instance(self, config):
        return baker.make(Agent, name="cfg1", config=config)

    @pytest.fixture
    def url(self, agent_instance):
        return reverse("agent-details", kwargs={"pk": agent_instance.pk})

    def test_get_outsider_gets_not_found(self, api_client, agent_instance, url):
        response = api_client.get(url)

        # Obscured as 404, not 403 - a non-member shouldn't be able to tell this dataset
        # apart from one that doesn't exist.
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_outsider_gets_identical_404_body_to_a_nonexistent_agent(self, api_client, agent_instance, url):
        # The two cases must be indistinguishable - not just the same status code, but the
        # same response body - or a non-member could tell them apart by comparing responses.
        existing_but_hidden = api_client.get(url)
        nonexistent = api_client.get(reverse("agent-details", kwargs={"pk": 9999}))

        assert existing_but_hidden.data == {"detail": "No Agent matches the given query."}
        assert existing_but_hidden.data == nonexistent.data

    def test_get_dataset_member_without_view_agent_gets_forbidden(self, api_client, user, agent_instance, url):
        # A member of the agent's dataset, but the role grants nothing agent-related.
        _grant_dataset_permission(user, agent_instance.dataset)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_existing_agent(self, api_client, user, agent_instance, url):
        _grant_dataset_permission(user, agent_instance.dataset, PERMISSIONS.AGENT.VIEW)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == agent_instance.name
        assert response.data["config"]

    def test_get_nonexistent_agent_returns_404(self, api_client):
        url = reverse("agent-details", kwargs={"pk": 9999})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_put_outsider_gets_not_found(self, api_client, agent_instance, url):
        response = api_client.put(url, {"name": "updated"}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_put_dataset_member_without_change_agent_gets_forbidden(self, api_client, user, agent_instance, url):
        _grant_dataset_permission(user, agent_instance.dataset)

        response = api_client.put(url, {"name": "updated"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_put_updates_agent(self, api_client, user, agent_instance, url, config):
        _grant_dataset_permission(user, agent_instance.dataset, PERMISSIONS.AGENT.CHANGE)
        dataset = agent_instance.dataset
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
            response = api_client.put(url, payload, format="json")

            assert response.status_code == status.HTTP_200_OK
            agent_instance.refresh_from_db()
            assert agent_instance.name == "updated"
            assert agent_instance.config == updated_config

    def test_put_cannot_move_agent_to_another_dataset(self, api_client, user, agent_instance, url, config):
        _grant_dataset_permission(user, agent_instance.dataset, PERMISSIONS.AGENT.CHANGE)
        original_dataset = agent_instance.dataset
        foreign_dataset = baker.make(DataSet)
        payload = {
            "name": "updated",
            "description": "description",
            "config": config,
            "dataset": foreign_dataset.id,
            "agent_type": "agent_1",
        }

        with patch("agent.serializers.customs.fields.AgentRegistry.get_plugin_classes", return_value=AGENT_CLASSES):
            response = api_client.put(url, payload, format="json")

            assert response.status_code == status.HTTP_200_OK
            assert response.data["dataset"] == original_dataset.id
            agent_instance.refresh_from_db()
            assert agent_instance.dataset == original_dataset

    def test_put_without_dataset_in_payload_updates_agent(self, api_client, user, agent_instance, url, config):
        _grant_dataset_permission(user, agent_instance.dataset, PERMISSIONS.AGENT.CHANGE)
        original_dataset = agent_instance.dataset
        payload = {
            "name": "updated",
            "description": "description",
            "config": config,
            "agent_type": "agent_1",
        }

        with patch("agent.serializers.customs.fields.AgentRegistry.get_plugin_classes", return_value=AGENT_CLASSES):
            response = api_client.put(url, payload, format="json")

            assert response.status_code == status.HTTP_200_OK
            agent_instance.refresh_from_db()
            assert agent_instance.name == "updated"
            assert agent_instance.dataset == original_dataset

    def test_put_removes_corrupted_flag_for_correct_data(self, api_client, user, url, config):
        dataset = baker.make(DataSet)
        _grant_dataset_permission(user, dataset, PERMISSIONS.AGENT.CHANGE)
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
            response = api_client.put(url, payload, format="json")

            assert response.status_code == status.HTTP_200_OK
            agent_instance.refresh_from_db()
            assert agent_instance.corrupted is False

    def test_put_nonexistent_returns_404(self, api_client):
        url = reverse("agent-details", kwargs={"pk": 9999})
        payload = {"name": "anything", "config": {"x": "y"}}

        response = api_client.put(url, payload, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_put_invalid_payload_returns_400(self, api_client, user, agent_instance, url):
        _grant_dataset_permission(user, agent_instance.dataset, PERMISSIONS.AGENT.CHANGE)
        payload = {"name": ""}

        response = api_client.put(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "config" in response.data

    def test_delete_outsider_gets_not_found(self, api_client, agent_instance, url):
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_dataset_member_without_delete_agent_gets_forbidden(self, api_client, user, agent_instance, url):
        _grant_dataset_permission(user, agent_instance.dataset)

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_existing_agent(self, api_client, user, agent_instance, url):
        _grant_dataset_permission(user, agent_instance.dataset, PERMISSIONS.AGENT.DELETE)

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        agent_instance = Agent.all_objects.get(pk=agent_instance.pk)
        assert agent_instance.deleted_at is not None

    def test_delete_nonexistent_agent_returns_404(self, api_client, url):
        url = reverse("agent-details", kwargs={"pk": 9999})
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestConversationView:
    @pytest.fixture
    def url(self, conversation):
        return reverse("conversation-details", kwargs={"conversation_id": conversation.id})

    def test_valid_post_returns_202(self, api_client, user, url, conversation):
        _grant_dataset_permission(user, conversation.data_set, PERMISSIONS.CONVERSATION.CONVERSE)
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

    def test_non_streaming_provider_disables_streaming_in_task(self, api_client, user, url, conversation):
        _grant_dataset_permission(user, conversation.data_set, PERMISSIONS.CONVERSATION.CONVERSE)
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

    def test_global_converse_holder_can_post(self, api_client, user, url, conversation):
        # Global grant, no per-dataset role anywhere - the other converse tests all go through
        # a DatasetUserRoleAssignment, so this covers has_dataset_perm's has_perm short-circuit.
        grant(user, PERMISSIONS.CONVERSATION.CONVERSE)
        payload = {
            "data_set_id": conversation.data_set.id,
            "question_message": "Hello?",
            "streaming": False,
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
        mock_task.assert_called_once()

    def test_invalid_payload_returns_400(self, api_client, url):
        payload = {"data_set_id": None}
        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "question_message" in response.data

    def test_owner_without_converse_permission_gets_forbidden(self, api_client, conversation, url):
        # Owns the conversation, but holds no role/permission on its dataset at all.
        payload = {
            "data_set_id": conversation.data_set.id,
            "question_message": "Hello?",
            "streaming": False,
        }
        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_agent_soft_deleted_returns_400(self, api_client, user, conversation, url):
        _grant_dataset_permission(user, conversation.data_set, PERMISSIONS.CONVERSATION.CONVERSE)
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

    def test_execution_conversation_post_returns_400(self, api_client, user, conversation, url):
        _grant_dataset_permission(user, conversation.data_set, PERMISSIONS.CONVERSATION.CONVERSE)
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

    def test_outsider_cannot_post_to_conversation_they_do_not_own(self, api_client):
        dataset = baker.make(DataSet)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        someone_elses_conversation = baker.make(Conversation, agent=agent)
        url = reverse("conversation-details", kwargs={"conversation_id": someone_elses_conversation.id})
        payload = {"data_set_id": dataset.id, "question_message": "How are you?", "streaming": False}

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_cannot_post_to_conversation_they_do_not_own(self, admin_api_client):
        dataset = baker.make(DataSet)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        someone_elses_conversation = baker.make(Conversation, agent=agent)
        url = reverse("conversation-details", kwargs={"conversation_id": someone_elses_conversation.id})
        payload = {"data_set_id": dataset.id, "question_message": "How are you?", "streaming": False}

        response = admin_api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_can_post_to_own_conversation_without_converse_permission(self, admin_api_client, admin_user):
        dataset = baker.make(DataSet)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        conversation = baker.make(Conversation, user=admin_user, agent=agent, data_set=dataset)
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

    def test_get_owner_can_view_own_conversation(self, api_client, conversation, url):
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == conversation.id

    def test_get_non_owner_without_view_all_gets_not_found(self, api_client, conversation, url):
        conversation.user = baker.make(User)
        conversation.save()

        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_global_view_all_holder_sees_conversations_they_do_not_own(self, api_client, user, conversation, url):
        conversation.user = baker.make(User)
        conversation.save()
        grant(user, PERMISSIONS.CONVERSATION.VIEW_ALL)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == conversation.id

    def test_get_per_dataset_view_all_holder_sees_that_datasets_conversations(
        self, api_client, user, conversation, url
    ):
        conversation.user = baker.make(User)
        conversation.save()
        _grant_dataset_permission(user, conversation.data_set, PERMISSIONS.CONVERSATION.VIEW_ALL)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == conversation.id


class TestConversationListView:
    @pytest.fixture
    def url(self):
        return reverse("conversation-list")

    def test_create_conversation_success(self, api_client, user, agent, dataset, url):
        _grant_dataset_permission(user, dataset, PERMISSIONS.CONVERSATION.CONVERSE)
        payload = {"agent_id": agent.id}

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["agent"]["id"] == agent.id

    def test_create_conversation_global_converse_holder_can_create(self, api_client, user, agent, url):
        grant(user, PERMISSIONS.CONVERSATION.CONVERSE)

        response = api_client.post(url, {"agent_id": agent.id}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["agent"]["id"] == agent.id

    def test_create_conversation_converse_on_another_dataset_does_not_grant_access(self, api_client, user, url):
        granted_dataset = baker.make(DataSet)
        _grant_dataset_permission(user, granted_dataset, PERMISSIONS.CONVERSATION.CONVERSE)
        other_dataset = baker.make(DataSet)
        agent_elsewhere = baker.make(Agent, deleted_at=None, dataset=other_dataset)

        response = api_client.post(url, {"agent_id": agent_elsewhere.id}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert not Conversation.objects.filter(agent=agent_elsewhere).exists()

    def test_create_conversation_invalid_payload(self, api_client, url):
        payload = {"wrong_field": 123}

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "agent_id" in response.data

    def test_create_conversation_with_deleted_agent(self, api_client, deleted_agent, url):
        payload = {"agent_id": deleted_agent.id}

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_conversation_outsider_gets_not_found(self, api_client, url):
        dataset = baker.make(DataSet)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        payload = {"agent_id": agent.id}

        response = api_client.post(url, payload, format="json")
        # Obscured as 404, not 403 - the agent id came from the caller, so a non-member
        # shouldn't be able to confirm it exists by probing this endpoint.
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_conversation_outsider_gets_identical_404_body_to_a_nonexistent_agent(self, api_client, url):
        # The two cases must be indistinguishable - not just the same status code, but the
        # same response body - or a non-member could tell them apart by comparing responses.
        agent = baker.make(Agent, deleted_at=None, dataset=baker.make(DataSet))

        existing_but_hidden = api_client.post(url, {"agent_id": agent.id}, format="json")
        nonexistent = api_client.post(url, {"agent_id": 9999}, format="json")

        assert existing_but_hidden.data == {"detail": "No Agent matches the given query."}
        assert existing_but_hidden.data == nonexistent.data

    def test_create_conversation_dataset_member_without_converse_gets_forbidden(self, api_client, user, url):
        dataset = baker.make(DataSet)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        _grant_dataset_permission(user, dataset)

        response = api_client.post(url, {"agent_id": agent.id}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_conversation_denial_leaves_no_conversation_behind(self, api_client, url):
        dataset = baker.make(DataSet)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        payload = {"agent_id": agent.id}

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert not Conversation.objects.filter(agent=agent).exists()

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

    def test_global_view_all_holder_sees_conversations_they_do_not_own(self, api_client, user, dataset):
        other_user = baker.make(User)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        others_conversation = baker.make(Conversation, user=other_user, agent=agent, data_set=dataset)
        grant(user, PERMISSIONS.CONVERSATION.VIEW_ALL)

        response = api_client.get(reverse("conversation-list"))

        assert response.status_code == status.HTTP_200_OK
        conversation_ids = [conv["id"] for conv in response.data["results"]]
        assert others_conversation.id in conversation_ids

    def test_per_dataset_view_all_holder_sees_only_that_datasets_conversations(self, api_client, user, dataset):
        other_user = baker.make(User)
        visible_agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        visible_conversation = baker.make(Conversation, user=other_user, agent=visible_agent, data_set=dataset)
        other_dataset = baker.make(DataSet)
        hidden_agent = baker.make(Agent, deleted_at=None, dataset=other_dataset)
        hidden_conversation = baker.make(Conversation, user=other_user, agent=hidden_agent, data_set=other_dataset)
        _grant_dataset_permission(user, dataset, PERMISSIONS.CONVERSATION.VIEW_ALL)

        response = api_client.get(reverse("conversation-list"))

        assert response.status_code == status.HTTP_200_OK
        conversation_ids = [conv["id"] for conv in response.data["results"]]
        assert visible_conversation.id in conversation_ids
        assert hidden_conversation.id not in conversation_ids

    def test_plain_converse_holder_without_view_all_sees_only_their_own_conversations(
        self, api_client, user, dataset
    ):
        other_user = baker.make(User)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        others_conversation = baker.make(Conversation, user=other_user, agent=agent, data_set=dataset)
        _grant_dataset_permission(user, dataset, PERMISSIONS.CONVERSATION.CONVERSE)

        response = api_client.get(reverse("conversation-list"))

        assert response.status_code == status.HTTP_200_OK
        conversation_ids = [conv["id"] for conv in response.data["results"]]
        assert others_conversation.id not in conversation_ids

    def test_list_attributes_each_conversation_to_its_owner(self, api_client, user, dataset, url):
        other_user = baker.make(User, email="colleague@example.com")
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        baker.make(Conversation, user=user, agent=agent, data_set=dataset)
        baker.make(Conversation, user=other_user, agent=agent, data_set=dataset)
        grant(user, PERMISSIONS.CONVERSATION.VIEW_ALL)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        owners = {conv["user_email"] for conv in response.data["results"]}
        assert owners == {user.email, "colleague@example.com"}

    def test_detail_attributes_the_conversation_to_its_owner(self, api_client, user, conversation):
        response = api_client.get(reverse("conversation-details", kwargs={"conversation_id": conversation.id}))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["user_email"] == user.email

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


class TestMessageFeedbackView:
    @pytest.fixture
    def message(self, conversation):
        return baker.make(Message, conversation=conversation, type=Message.MessageType.AI, text="Hi there")

    @pytest.fixture
    def url(self, message):
        return f"/api/messages/{message.id}/feedback/"

    def test_owner_can_leave_feedback(self, api_client, message, url):
        payload = {"rating": 5, "feedback": "Great answer"}

        response = api_client.patch(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        message.refresh_from_db()
        assert message.rating == 5
        assert message.feedback == "Great answer"

    def test_non_owner_gets_not_found(self, api_client, message, url):
        # Obscured as 404 - probing message ids shouldn't reveal which ones exist.
        message.conversation.user = baker.make(User)
        message.conversation.save()
        payload = {"rating": 5, "feedback": "Great answer"}

        response = api_client.patch(url, payload, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_who_is_not_the_owner_gets_not_found(self, admin_api_client, message):
        url = f"/api/messages/{message.id}/feedback/"
        payload = {"rating": 5, "feedback": "Great answer"}

        response = admin_api_client.patch(url, payload, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_message_returns_404(self, api_client):
        response = api_client.patch("/api/messages/99999/feedback/", {"rating": 5, "feedback": "x"}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_non_owner_gets_identical_404_body_to_a_nonexistent_message(self, api_client, message, url):
        message.conversation.user = baker.make(User)
        message.conversation.save()

        existing_but_hidden = api_client.patch(url, {"rating": 5, "feedback": "x"}, format="json")
        nonexistent = api_client.patch("/api/messages/99999/feedback/", {"rating": 5, "feedback": "x"}, format="json")

        assert existing_but_hidden.data == {"detail": "No Message matches the given query."}
        assert existing_but_hidden.data == nonexistent.data

    def test_invalid_payload_returns_400(self, api_client, message, url):
        response = api_client.patch(url, {"rating": 6}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
