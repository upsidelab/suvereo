from unittest.mock import patch

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone
from enthusiast_common.agentic_execution import BaseAgenticExecutionDefinition, ExecutionInputType, ExecutionResult
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.models import DatasetRole, DatasetUserRoleAssignment, User
from account.tests.helpers import grant
from agent.agentic_execution.registry import AgenticExecutionDefinitionRegistry
from agent.agentic_execution.services import FileUploadNotSupportedError, UnsupportedFileTypeError
from agent.conversation.models.conversation import Conversation
from agent.models.agent import Agent
from agent.models.agentic_execution import AgenticExecution
from catalog.models import DataSet

pytestmark = pytest.mark.django_db

DUMMY_AGENT_TYPE = "dummy-agent-type"


class DummyExecutionInput(ExecutionInputType):
    required_field: str
    optional_field: int = 10


class DummyExecution(BaseAgenticExecutionDefinition):
    EXECUTION_KEY = "dummy"
    AGENT_KEY = DUMMY_AGENT_TYPE
    NAME = "Dummy Execution"
    INPUT_TYPE = DummyExecutionInput

    def run(self, input_data: DummyExecutionInput) -> ExecutionResult:
        return ExecutionResult(output={})


class AllDefaultsExecutionInput(ExecutionInputType):
    optional_field: int = 10


class AllDefaultsExecution(BaseAgenticExecutionDefinition):
    EXECUTION_KEY = "all-defaults"
    AGENT_KEY = DUMMY_AGENT_TYPE
    NAME = "All Defaults Execution"
    INPUT_TYPE = AllDefaultsExecutionInput

    def run(self, input_data: AllDefaultsExecutionInput) -> ExecutionResult:
        return ExecutionResult(output={})


def _permission(codename: str) -> Permission:
    app_label, name = codename.split(".")
    return Permission.objects.get(codename=name, content_type__app_label=app_label)


def _grant_dataset_permission(user, dataset, *codenames: str) -> DatasetRole:
    role = baker.make(DatasetRole)
    role.permissions.set([_permission(codename) for codename in codenames])
    baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)
    return role


def _client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def user():
    return baker.make(User, is_superuser=False)


@pytest.fixture
def api_client(user):
    return _client_for(user)


@pytest.fixture
def outsider_api_client():
    """A logged-in user with no relationship whatsoever to `dataset`."""
    return _client_for(baker.make(User, is_superuser=False))


@pytest.fixture
def dataset():
    return baker.make(DataSet)


@pytest.fixture
def member_api_client(dataset):
    """A member of `dataset` holding a role that grants no agentic-execution permission."""
    member = baker.make(User, is_superuser=False)
    _grant_dataset_permission(member, dataset)
    return _client_for(member)


@pytest.fixture
def agent(dataset):
    return baker.make(Agent, deleted_at=None, dataset=dataset, agent_type=DUMMY_AGENT_TYPE)


@pytest.fixture
def execution(agent, user, dataset):
    conversation = baker.make(Conversation, user=user, agent=agent, data_set=dataset)
    return baker.make(AgenticExecution, agent=agent, conversation=conversation, input={"required_field": "hello"})


class TestAgenticExecutionListView:
    @pytest.fixture
    def url(self):
        return reverse("agentic-execution-list")

    def test_returns_200(self, api_client, execution, url):
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["id"] == execution.id

    def test_filters_by_agent_id(self, api_client, user, dataset, url):
        agent1 = baker.make(Agent, deleted_at=None, dataset=dataset)
        agent2 = baker.make(Agent, deleted_at=None, dataset=dataset)
        conv1 = baker.make(Conversation, user=user, agent=agent1, data_set=dataset)
        conv2 = baker.make(Conversation, user=user, agent=agent2, data_set=dataset)
        exec1 = baker.make(AgenticExecution, agent=agent1, conversation=conv1, input={})
        baker.make(AgenticExecution, agent=agent2, conversation=conv2, input={})

        response = api_client.get(url, {"agent_id": agent1.id})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["id"] == exec1.id

    def test_returns_401_when_unauthenticated(self, url):
        response = APIClient().get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_excludes_executions_belonging_to_other_user(self, api_client, agent, dataset, url):
        other_user = baker.make(User)
        conversation = baker.make(Conversation, user=other_user, agent=agent, data_set=dataset)
        baker.make(AgenticExecution, agent=agent, conversation=conversation, input={})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

    def test_global_view_all_holder_sees_other_users_executions(self, agent, dataset, url):
        other_user = baker.make(User)
        conversation = baker.make(Conversation, user=other_user, agent=agent, data_set=dataset)
        others_execution = baker.make(AgenticExecution, agent=agent, conversation=conversation, input={})
        watcher = baker.make(User, is_superuser=False)
        grant(watcher, PERMISSIONS.AGENTIC_EXECUTION.VIEW_ALL)

        response = _client_for(watcher).get(url)

        assert response.status_code == status.HTTP_200_OK
        assert others_execution.id in [result["id"] for result in response.data["results"]]

    def test_per_dataset_view_all_holder_sees_only_that_datasets_executions(self, agent, dataset, url):
        other_user = baker.make(User)
        visible_conversation = baker.make(Conversation, user=other_user, agent=agent, data_set=dataset)
        visible_execution = baker.make(AgenticExecution, agent=agent, conversation=visible_conversation, input={})
        other_dataset = baker.make(DataSet)
        hidden_agent = baker.make(Agent, deleted_at=None, dataset=other_dataset)
        hidden_conversation = baker.make(Conversation, user=other_user, agent=hidden_agent, data_set=other_dataset)
        hidden_execution = baker.make(
            AgenticExecution, agent=hidden_agent, conversation=hidden_conversation, input={}
        )
        watcher = baker.make(User, is_superuser=False)
        _grant_dataset_permission(watcher, dataset, PERMISSIONS.AGENTIC_EXECUTION.VIEW_ALL)

        response = _client_for(watcher).get(url)

        assert response.status_code == status.HTTP_200_OK
        execution_ids = [result["id"] for result in response.data["results"]]
        assert visible_execution.id in execution_ids
        assert hidden_execution.id not in execution_ids

    def test_create_holder_without_view_all_sees_only_their_own_executions(self, api_client, user, agent, dataset, url):
        _grant_dataset_permission(user, dataset, PERMISSIONS.AGENTIC_EXECUTION.CREATE)
        own_conversation = baker.make(Conversation, user=user, agent=agent, data_set=dataset)
        own_execution = baker.make(AgenticExecution, agent=agent, conversation=own_conversation, input={})
        others_conversation = baker.make(Conversation, user=baker.make(User), agent=agent, data_set=dataset)
        others_execution = baker.make(AgenticExecution, agent=agent, conversation=others_conversation, input={})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        execution_ids = [result["id"] for result in response.data["results"]]
        assert own_execution.id in execution_ids
        assert others_execution.id not in execution_ids

    def test_attributes_each_execution_to_the_user_who_started_it(self, agent, dataset, url):
        starter = baker.make(User, email="starter@example.com")
        conversation = baker.make(Conversation, user=starter, agent=agent, data_set=dataset)
        baker.make(AgenticExecution, agent=agent, conversation=conversation, input={})
        watcher = baker.make(User, is_superuser=False)
        grant(watcher, PERMISSIONS.AGENTIC_EXECUTION.VIEW_ALL)

        response = _client_for(watcher).get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"][0]["user_email"] == "starter@example.com"

    def test_returns_results_ordered_newest_first(self, api_client, user, agent, dataset, url):
        conv1 = baker.make(Conversation, user=user, agent=agent, data_set=dataset)
        conv2 = baker.make(Conversation, user=user, agent=agent, data_set=dataset)
        older = baker.make(AgenticExecution, agent=agent, conversation=conv1, input={})
        newer = baker.make(AgenticExecution, agent=agent, conversation=conv2, input={})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        ids = [r["id"] for r in response.data["results"]]
        assert ids.index(newer.id) < ids.index(older.id)


class TestAgenticExecutionDetailView:
    @pytest.fixture
    def url(self, execution):
        return reverse("agentic-execution-detail", kwargs={"pk": execution.pk})

    def test_returns_200(self, api_client, execution, url):
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == execution.id
        assert response.data["status"] == AgenticExecution.Status.PENDING

    def test_returns_all_expected_fields(self, api_client, execution, url):
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        for field in ("id", "agent", "execution_key", "conversation", "status", "input", "result",
                      "failure_code", "failure_explanation", "celery_task_id",
                      "started_at", "finished_at", "duration_seconds", "user_email"):
            assert field in response.data

    def test_returns_404_for_nonexistent(self, api_client):
        url = reverse("agentic-execution-detail", kwargs={"pk": 99999})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_401_when_unauthenticated(self, execution):
        url = reverse("agentic-execution-detail", kwargs={"pk": execution.pk})

        response = APIClient().get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_404_for_other_users_execution(self, api_client, agent, dataset):
        other_user = baker.make(User)
        conversation = baker.make(Conversation, user=other_user, agent=agent, data_set=dataset)
        other_execution = baker.make(AgenticExecution, agent=agent, conversation=conversation, input={})
        url = reverse("agentic-execution-detail", kwargs={"pk": other_execution.pk})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_global_view_all_holder_can_fetch_other_users_execution(self, execution, url):
        watcher = baker.make(User, is_superuser=False)
        grant(watcher, PERMISSIONS.AGENTIC_EXECUTION.VIEW_ALL)

        response = _client_for(watcher).get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == execution.id

    def test_per_dataset_view_all_holder_can_fetch_other_users_execution(self, execution, dataset, url):
        watcher = baker.make(User, is_superuser=False)
        _grant_dataset_permission(watcher, dataset, PERMISSIONS.AGENTIC_EXECUTION.VIEW_ALL)

        response = _client_for(watcher).get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == execution.id

    def test_per_dataset_view_all_on_another_dataset_does_not_grant_access(self, execution, url):
        watcher = baker.make(User, is_superuser=False)
        _grant_dataset_permission(watcher, baker.make(DataSet), PERMISSIONS.AGENTIC_EXECUTION.VIEW_ALL)

        response = _client_for(watcher).get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAgenticExecutionDefinitionTypesView:
    @pytest.fixture
    def url(self, agent):
        return reverse("agentic-execution-definitions", kwargs={"agent_id": agent.pk})

    @pytest.fixture(autouse=True)
    def mock_registry(self):
        with patch(
            "agent.agentic_execution.services.AgenticExecutionDefinitionRegistry.get_by_agent_type",
            return_value=[DummyExecution, AllDefaultsExecution],
        ) as mock:
            yield mock

    @pytest.fixture(autouse=True)
    def create_permission(self, user, dataset):
        return _grant_dataset_permission(user, dataset, PERMISSIONS.AGENTIC_EXECUTION.CREATE)

    def test_returns_200_with_execution_types(self, api_client, url):
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_returns_expected_fields_for_each_type(self, api_client, url):
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        for item in response.data:
            for field in ("key", "name", "description", "input_schema"):
                assert field in item

    def test_returns_correct_keys(self, api_client, url):
        response = api_client.get(url)

        keys = [item["key"] for item in response.data]
        assert "dummy" in keys
        assert "all-defaults" in keys

    def test_returns_404_for_nonexistent_agent(self, api_client):
        url = reverse("agentic-execution-definitions", kwargs={"agent_id": 99999})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_401_when_unauthenticated(self, agent):
        url = reverse("agentic-execution-definitions", kwargs={"agent_id": agent.pk})

        response = APIClient().get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_404_for_dataset_outsider(self, outsider_api_client, url):
        response = outsider_api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_403_for_dataset_member_without_create_permission(self, member_api_client, url):
        response = member_api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_global_create_holder_can_list_definitions(self, dataset, url):
        holder = baker.make(User, is_superuser=False)
        grant(holder, PERMISSIONS.AGENTIC_EXECUTION.CREATE)

        response = _client_for(holder).get(url)

        assert response.status_code == status.HTTP_200_OK


class TestStartAgenticExecutionView:
    @pytest.fixture
    def url(self, agent):
        return reverse("agentic-execution-start", kwargs={"agent_id": agent.pk})

    @pytest.fixture(autouse=True)
    def mock_registry(self):
        with patch.object(AgenticExecutionDefinitionRegistry, "get_by_key", return_value=DummyExecution) as mock:
            yield mock

    @pytest.fixture(autouse=True)
    def create_permission(self, user, dataset):
        return _grant_dataset_permission(user, dataset, PERMISSIONS.AGENTIC_EXECUTION.CREATE)

    def test_returns_404_for_nonexistent_agent(self, api_client):
        url = reverse("agentic-execution-start", kwargs={"agent_id": 99999})

        response = api_client.post(
            url, {"execution_key": "dummy", "input": {"required_field": "hello"}}, format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_404_for_soft_deleted_agent(self, api_client, dataset):
        deleted_agent = baker.make(Agent, deleted_at=timezone.now(), dataset=dataset, agent_type=DUMMY_AGENT_TYPE)
        url = reverse("agentic-execution-start", kwargs={"agent_id": deleted_agent.pk})

        response = api_client.post(
            url, {"execution_key": "dummy", "input": {"required_field": "hello"}}, format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_400_when_execution_key_has_no_class(self, api_client, url, mock_registry):
        mock_registry.side_effect = KeyError("no class")

        response = api_client.post(
            url, {"execution_key": "unknown", "input": {"required_field": "hello"}}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_returns_400_when_required_input_field_missing(self, api_client, url):
        response = api_client.post(url, {"execution_key": "dummy", "input": {}}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "required_field" in response.data["input"]

    def test_returns_400_when_input_field_has_wrong_type(self, api_client, url):
        response = api_client.post(
            url,
            {"execution_key": "dummy", "input": {"required_field": "ok", "optional_field": "not-an-int"}},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "optional_field" in response.data["input"]

    def test_returns_400_when_input_has_extra_fields(self, api_client, url):
        response = api_client.post(
            url,
            {"execution_key": "dummy", "input": {"required_field": "ok", "unknown_field": "surprise"}},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "unknown_field" in response.data["input"]

    def test_returns_400_when_service_raises_file_upload_not_supported(self, api_client, url):
        with patch("agent.agentic_execution.views.AgenticExecutionService.start", side_effect=FileUploadNotSupportedError()):
            response = api_client.post(
                url, {"execution_key": "dummy", "input": {"required_field": "hello"}}, format="json"
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "file upload" in response.data["detail"].lower()

    def test_returns_400_when_service_raises_unsupported_file_type(self, api_client, url):
        with patch("agent.agentic_execution.views.AgenticExecutionService.start", side_effect=UnsupportedFileTypeError(".xyz", [".pdf"])):
            response = api_client.post(
                url, {"execution_key": "dummy", "input": {"required_field": "hello"}}, format="json"
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_returns_401_when_unauthenticated(self, agent):
        url = reverse("agentic-execution-start", kwargs={"agent_id": agent.pk})

        response = APIClient().post(
            url, {"execution_key": "dummy", "input": {"required_field": "hello"}}, format="json"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_happy_path_returns_202_with_execution_data(self, api_client, url, user, agent, dataset):
        with patch("agent.agentic_execution.views.AgenticExecutionService.start") as mock_start, \
             patch("agent.agentic_execution.services.run_agentic_execution_task.delay"):
            conversation = baker.make(Conversation, user=user, agent=agent, data_set=dataset)
            baker.make("agent.ConversationFile", conversation=conversation, is_hidden=False)
            execution = baker.make(AgenticExecution, agent=agent, conversation=conversation, input={"required_field": "hello"})
            mock_start.return_value = execution
            response = api_client.post(
                url, {"execution_key": "dummy", "input": {"required_field": "hello"}}, format="json"
            )

        assert response.status_code == status.HTTP_202_ACCEPTED

    def test_happy_path_passes_correct_args_to_service(self, api_client, url, agent, user):
        with patch("agent.agentic_execution.views.AgenticExecutionService.start") as mock_start, \
             patch("agent.agentic_execution.services.run_agentic_execution_task.delay"):
            mock_start.return_value = baker.make(AgenticExecution, agent=agent, execution_key="dummy")
            api_client.post(
                url, {"execution_key": "dummy", "input": {"required_field": "hello"}}, format="json"
            )

        mock_start.assert_called_once()
        call_kwargs = mock_start.call_args.kwargs
        assert call_kwargs["agent"] == agent
        assert call_kwargs["user"] == user
        assert call_kwargs["execution_key"] == "dummy"
        assert call_kwargs["validated_input"] == {"required_field": "hello", "optional_field": 10}
        assert call_kwargs["uploaded_files"] == []

    def test_dataset_outsider_cannot_start_an_execution(self, outsider_api_client, url):
        with patch("agent.agentic_execution.views.AgenticExecutionService.start") as mock_start:
            response = outsider_api_client.post(
                url, {"execution_key": "dummy", "input": {"required_field": "hello"}}, format="json"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        mock_start.assert_not_called()

    def test_outsider_gets_identical_404_body_to_a_nonexistent_agent(self, outsider_api_client, url):
        outsider_response = outsider_api_client.post(
            url, {"execution_key": "dummy", "input": {"required_field": "hello"}}, format="json"
        )
        missing_response = outsider_api_client.post(
            reverse("agentic-execution-start", kwargs={"agent_id": 99999}),
            {"execution_key": "dummy", "input": {"required_field": "hello"}},
            format="json",
        )

        assert outsider_response.status_code == missing_response.status_code == status.HTTP_404_NOT_FOUND
        assert outsider_response.data == missing_response.data

    def test_dataset_member_without_create_permission_gets_403(self, member_api_client, url):
        with patch("agent.agentic_execution.views.AgenticExecutionService.start") as mock_start:
            response = member_api_client.post(
                url, {"execution_key": "dummy", "input": {"required_field": "hello"}}, format="json"
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        mock_start.assert_not_called()

    def test_view_all_holder_without_create_permission_cannot_start_an_execution(self, dataset, url):
        watcher = baker.make(User, is_superuser=False)
        _grant_dataset_permission(watcher, dataset, PERMISSIONS.AGENTIC_EXECUTION.VIEW_ALL)

        response = _client_for(watcher).post(
            url, {"execution_key": "dummy", "input": {"required_field": "hello"}}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_global_create_holder_can_start_an_execution(self, agent, url):
        holder = baker.make(User, is_superuser=False)
        grant(holder, PERMISSIONS.AGENTIC_EXECUTION.CREATE)

        with patch("agent.agentic_execution.views.AgenticExecutionService.start") as mock_start, \
             patch("agent.agentic_execution.services.run_agentic_execution_task.delay"):
            mock_start.return_value = baker.make(AgenticExecution, agent=agent, execution_key="dummy")
            response = _client_for(holder).post(
                url, {"execution_key": "dummy", "input": {"required_field": "hello"}}, format="json"
            )

        assert response.status_code == status.HTTP_202_ACCEPTED
