from unittest.mock import patch

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.models import DatasetRole, DatasetUserRoleAssignment, User
from agent.models import Agent
from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.models import DataSet, Integration
from catalog.tests.integration_mocks import MockSingleInstanceIntegration, MockToolProvidingIntegration

pytestmark = pytest.mark.django_db


class DummyAgent:
    AGENT_KEY = "dummy_agent"
    NAME = "Dummy agent"
    AGENT_ARGS = None
    PROMPT_INPUT = None
    TOOLS = []
    FILE_UPLOAD = False


@pytest.fixture(autouse=True)
def registered_plugins():
    with (
        patch.object(
            IntegrationPluginRegistry,
            "get_plugin_classes",
            return_value=[MockSingleInstanceIntegration, MockToolProvidingIntegration],
        ),
        patch("agent.serializers.customs.fields.AgentRegistry.get_plugin_classes", return_value=[DummyAgent]),
        patch("agent.serializers.configuration.AgentRegistry.get_agent_class_by_type", return_value=DummyAgent),
    ):
        yield


@pytest.fixture
def user():
    return baker.make(User, is_superuser=False)


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def dataset():
    return baker.make(DataSet)


def _grant(user, dataset, *codenames: str) -> None:
    permissions = [
        Permission.objects.get(codename=codename.split(".")[1], content_type__app_label=codename.split(".")[0])
        for codename in codenames
    ]
    role = baker.make(DatasetRole)
    role.permissions.set(permissions)
    baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)


def _tool_providing_integration(dataset) -> Integration:
    return baker.make(Integration, dataset=dataset, type="mock_tools", allows_multiple_instances=True)


def _payload(dataset, integrations) -> dict:
    return {
        "name": "Support",
        "config": {"agent_args": {}, "prompt_input": {}, "tools": []},
        "dataset": dataset.id,
        "agent_type": "dummy_agent",
        "tool_providing_integrations": [integration.id for integration in integrations],
    }


class TestAgentToolProvidingIntegrationSelection:
    def test_post_saves_the_selected_tool_providing_integrations(self, api_client, user, dataset):
        _grant(user, dataset, PERMISSIONS.AGENT.ADD)
        linear, github = _tool_providing_integration(dataset), _tool_providing_integration(dataset)

        response = api_client.post(reverse("agents"), _payload(dataset, [linear]), format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["tool_providing_integrations"] == [linear.id]
        assert list(Agent.objects.get(pk=response.data["id"]).tool_providing_integrations.all()) == [linear]
        assert github.agents.count() == 0

    def test_post_without_tool_providing_integrations_selects_none(self, api_client, user, dataset):
        _grant(user, dataset, PERMISSIONS.AGENT.ADD)
        _tool_providing_integration(dataset)
        payload = _payload(dataset, [])
        del payload["tool_providing_integrations"]

        response = api_client.post(reverse("agents"), payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["tool_providing_integrations"] == []

    @pytest.mark.parametrize(
        "integration_factory",
        [
            lambda dataset: _tool_providing_integration(baker.make(DataSet)),
            lambda dataset: baker.make(Integration, dataset=dataset, type="mock_single"),
        ],
        ids=["another data set", "provides no tools"],
    )
    def test_post_rejects_a_tool_providing_integration_the_agent_cannot_select(
        self, api_client, user, dataset, integration_factory
    ):
        _grant(user, dataset, PERMISSIONS.AGENT.ADD)

        response = api_client.post(reverse("agents"), _payload(dataset, [integration_factory(dataset)]), format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "tool_providing_integrations" in response.data

    def test_another_data_sets_tool_providing_integration_reads_like_a_missing_one(self, api_client, user, dataset):
        _grant(user, dataset, PERMISSIONS.AGENT.ADD)
        foreign = _tool_providing_integration(baker.make(DataSet))
        missing_id = foreign.id + 1000

        foreign_response = api_client.post(reverse("agents"), _payload(dataset, [foreign]), format="json")
        payload = _payload(dataset, [])
        payload["tool_providing_integrations"] = [missing_id]
        missing_response = api_client.post(reverse("agents"), payload, format="json")

        assert foreign_response.data["tool_providing_integrations"] == [
            f'Invalid pk "{foreign.id}" - object does not exist.'
        ]
        assert missing_response.data["tool_providing_integrations"] == [
            f'Invalid pk "{missing_id}" - object does not exist.'
        ]

    def test_put_replaces_the_selection(self, api_client, user, dataset):
        _grant(user, dataset, PERMISSIONS.AGENT.CHANGE)
        linear, github = _tool_providing_integration(dataset), _tool_providing_integration(dataset)
        agent = baker.make(Agent, dataset=dataset, agent_type="dummy_agent", config={})
        agent.tool_providing_integrations.set([linear])

        response = api_client.put(
            reverse("agent-details", kwargs={"pk": agent.pk}), _payload(dataset, [github]), format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert list(agent.tool_providing_integrations.all()) == [github]


class TestSelectableToolProvidingIntegrationsView:
    def test_lists_only_the_data_sets_tool_providing_integrations(self, api_client, user, dataset):
        _grant(user, dataset, PERMISSIONS.AGENT.VIEW)
        tools = _tool_providing_integration(dataset)
        baker.make(Integration, dataset=dataset, type="mock_single")
        _tool_providing_integration(baker.make(DataSet))

        response = api_client.get(reverse("agent-tool-providing-integrations"), {"dataset": dataset.id})

        assert response.status_code == status.HTTP_200_OK
        assert response.data == [{"id": tools.id, "name": "Mock Tools"}]

    def test_member_without_view_agent_gets_forbidden(self, api_client, user, dataset):
        _grant(user, dataset)

        response = api_client.get(reverse("agent-tool-providing-integrations"), {"dataset": dataset.id})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_outsider_gets_not_found(self, api_client, dataset):
        response = api_client.get(reverse("agent-tool-providing-integrations"), {"dataset": dataset.id})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_missing_dataset_is_a_bad_request(self, api_client):
        response = api_client.get(reverse("agent-tool-providing-integrations"))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
