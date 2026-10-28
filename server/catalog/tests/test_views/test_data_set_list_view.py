from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse
from suvereo_common.utils import RequiredFieldsModel
from model_bakery import baker
from pydantic import Field
from rest_framework import status

from account.authorization import PERMISSIONS
from account.models import DatasetGroupRoleAssignment, DatasetRole, DatasetUserRoleAssignment, UserGroup
from account.tests.helpers import grant
from account.tests.public_permission_codes_contract import (
    AGENT_VIEW,
    CONVERSATION_CONVERSE,
    DATASET_SCOPED_CONTRACT,
)
from agent.core.registries.agents.agent_registry import AgentRegistry
from agent.core.registries.embeddings.embedding_provider_registry import EmbeddingProviderRegistry
from agent.models import Agent
from catalog.models import DataSet

pytestmark = pytest.mark.django_db


def _permission(codename: str) -> Permission:
    app_label, name = codename.split(".")
    return Permission.objects.get(codename=name, content_type__app_label=app_label)


class MockAgentArgs(RequiredFieldsModel):
    test: str = Field(default="")


class MockAgentClass:
    AGENT_KEY = "dummy_agent_type"
    NAME= "Dummy Agent"
    AGENT_ARGS = MockAgentArgs
    PROMPT_INPUT = MockAgentArgs
    TOOLS = []
    FILE_UPLOAD = False


@pytest.mark.django_db
class TestDataSetListViewPost:
    MOCK_AGENT_CLASS = MockAgentClass

    @pytest.fixture
    def url(self):
        return reverse("data_set_list")

    @pytest.fixture
    def payload(self):
        return {"name": "New DataSet"}

    @pytest.fixture
    def payload_preconfigure_agents(self):
        return {"name": "New DataSet", "preconfigure_agents": True}

    def test_admin_can_create_dataset(self, admin_api_client, url, payload):
        response = admin_api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert DataSet.objects.filter(name="New DataSet").exists()

    def test_non_admin_cannot_create_dataset(self, api_client, url, payload):
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not DataSet.objects.filter(name="New DataSet").exists()

    def test_user_with_add_dataset_permission_can_create_dataset(self, api_client, user, url, payload):
        grant(user, PERMISSIONS.DATA_SET.ADD)

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert DataSet.objects.filter(name="New DataSet").exists()

    def test_admin_dataset_creation_with_no_agent_preconfiguration(self, admin_api_client, url, payload):
        response = admin_api_client.post(url, payload, format="json")

        dataset = DataSet.objects.get(name="New DataSet")
        assert response.status_code == status.HTTP_201_CREATED
        assert not Agent.objects.filter(dataset=dataset).exists()

    @patch.object(AgentRegistry, "get_plugin_classes")
    @override_settings(
        AVAILABLE_AGENTS=['dummy_agent_directory_path.DummyAgent']
    )
    def test_admin_dataset_creation_with_agent_preconfiguration(
        self, mock_agent_registry, admin_api_client, url, payload_preconfigure_agents
    ):
        mock_agent_registry.return_value = [self.MOCK_AGENT_CLASS]
        response = admin_api_client.post(url, payload_preconfigure_agents, format="json")

        dataset = DataSet.objects.get(name="New DataSet")
        assert response.status_code == status.HTTP_201_CREATED
        mock_agent_registry.assert_called()

        assert Agent.objects.filter(dataset=dataset).exists()

    @patch.object(EmbeddingProviderRegistry, "provider_class_by_name")
    def test_dataset_creation_with_constrained_vector_size_success(
        self, mock_provider_class_by_name, admin_api_client, url
    ):
        mock_provider = MagicMock()
        mock_provider.vector_size_constraints.return_value = {"constrained-embed": [1024]}
        mock_provider_class_by_name.return_value = mock_provider

        payload = {
            "name": "Constrained DataSet",
            "embedding_provider": "MockProvider",
            "embedding_model": "constrained-embed",
            "embedding_vector_dimensions": 1024,
        }
        response = admin_api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert DataSet.objects.filter(name="Constrained DataSet").exists()

    @patch.object(EmbeddingProviderRegistry, "provider_class_by_name")
    def test_dataset_creation_with_constrained_vector_size_failure(
        self, mock_provider_class_by_name, admin_api_client, url
    ):
        mock_provider = MagicMock()
        mock_provider.vector_size_constraints.return_value = {"constrained-embed": [1024]}
        mock_provider_class_by_name.return_value = mock_provider

        payload = {
            "name": "Constrained DataSet",
            "embedding_provider": "MockProvider",
            "embedding_model": "constrained-embed",
            "embedding_vector_dimensions": 512,
        }
        response = admin_api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not DataSet.objects.filter(name="Constrained DataSet").exists()


class TestDataSetListViewGet:
    @pytest.fixture
    def url(self):
        return reverse("data_set_list")

    def _ids(self, response):
        return {item["id"] for item in response.data["results"]}

    def test_plain_user_sees_no_datasets(self, api_client, url):
        baker.make(DataSet)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert self._ids(response) == set()

    def test_user_sees_only_their_assigned_dataset(self, api_client, user, url):
        visible = baker.make(DataSet)
        baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=visible, role=role)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert self._ids(response) == {visible.id}

    def test_user_sees_dataset_via_group_assignment(self, api_client, user, url):
        group = baker.make(UserGroup)
        group.members.add(user)
        visible = baker.make(DataSet)
        baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetGroupRoleAssignment, group=group, dataset=visible, role=role)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert self._ids(response) == {visible.id}

    def test_global_view_dataset_holder_sees_all_datasets(self, api_client, user, url):
        grant(user, PERMISSIONS.DATA_SET.VIEW)
        datasets = baker.make(DataSet, _quantity=2)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert self._ids(response) == {d.id for d in datasets}

    def test_admin_sees_all_datasets(self, admin_api_client, url):
        datasets = baker.make(DataSet, _quantity=2)

        response = admin_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert self._ids(response) == {d.id for d in datasets}

    def test_temporary_datasets_are_hidden_even_from_admins(self, admin_api_client, url):
        listed = baker.make(DataSet)
        baker.make(DataSet, is_temporary=True)

        response = admin_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert self._ids(response) == {listed.id}


class TestDataSetListViewGetPermissionsField:
    """Every row carries the requesting user's dataset-scoped codes on that data set.

    This is what the frontend gates per-data-set controls on - `GET /api/account` reports global
    grants only, so a code held through a role would be invisible to it.
    """

    @pytest.fixture
    def url(self):
        return reverse("data_set_list")

    def _permissions_by_id(self, response):
        return {item["id"]: item["permissions"] for item in response.data["results"]}

    def test_reports_the_codes_a_role_grants_on_the_dataset_it_was_assigned_on(self, api_client, user, url):
        assigned = baker.make(DataSet)
        also_visible = baker.make(DataSet)
        role = baker.make(DatasetRole)
        role.permissions.add(_permission(PERMISSIONS.AGENT.VIEW), _permission(PERMISSIONS.CONVERSATION.CONVERSE))
        baker.make(DatasetUserRoleAssignment, user=user, dataset=assigned, role=role)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=also_visible, role=baker.make(DatasetRole))

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert self._permissions_by_id(response) == {
            assigned.id: [AGENT_VIEW, CONVERSATION_CONVERSE],
            also_visible.id: [],
        }

    def test_global_grant_reports_on_every_visible_dataset(self, api_client, user, url):
        grant(user, PERMISSIONS.DATA_SET.VIEW, PERMISSIONS.AGENT.VIEW)
        baker.make(DataSet, _quantity=2)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert list(self._permissions_by_id(response).values()) == [[AGENT_VIEW], [AGENT_VIEW]]

    def test_admin_holds_every_dataset_scoped_code(self, admin_api_client, url):
        baker.make(DataSet)

        response = admin_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert set(response.data["results"][0]["permissions"]) == DATASET_SCOPED_CONTRACT

    def test_permissions_cannot_be_set_on_create(self, admin_api_client, url):
        response = admin_api_client.post(url, {"name": "New DataSet", "permissions": [AGENT_VIEW]}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert set(response.data["permissions"]) == DATASET_SCOPED_CONTRACT
