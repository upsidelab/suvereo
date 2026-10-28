from unittest.mock import patch

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from suvereo_common.config import FunctionToolConfig
from suvereo_common.tools import BaseFunctionTool
from suvereo_common.utils import RequiredFieldsModel
from model_bakery import baker
from pydantic import Field
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.models import DatasetRole, DatasetUserRoleAssignment, User
from agent.models.agent import Agent
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


class DummyAgentBase:
    AGENT_ARGS = AgentArgs
    PROMPT_INPUT = PromptInput
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

    def test_get_a_temporary_datasets_agents_is_not_found(self, admin_api_client, url):
        sandbox = baker.make(DataSet, is_temporary=True)
        baker.make(Agent, dataset=sandbox, config={})

        response = admin_api_client.get(f"{url}?dataset={sandbox.pk}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

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

    def test_post_on_a_temporary_dataset_is_rejected(self, admin_api_client, url):
        sandbox = baker.make(DataSet, is_temporary=True)

        response = admin_api_client.post(url, {"dataset": sandbox.id}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not Agent.all_objects.filter(dataset=sandbox).exists()

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

    @pytest.mark.parametrize("method", ["get", "put", "delete"])
    def test_an_agent_on_a_temporary_dataset_is_not_found(self, admin_api_client, config, method):
        agent = baker.make(Agent, config=config, dataset=baker.make(DataSet, is_temporary=True))

        response = getattr(admin_api_client, method)(reverse("agent-details", kwargs={"pk": agent.pk}), format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Agent.all_objects.get(pk=agent.pk).deleted_at is None

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
