from unittest.mock import patch

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.models import DatasetRole, DatasetUserRoleAssignment, User
from account.tests.helpers import grant
from agent.conversation.models import Conversation, Message
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
                "agent.conversation.views.respond_to_user_message_task.apply_async",
                return_value=type("obj", (), {"id": "fake-task-id"}),
            ) as mock_task,
            patch("agent.conversation.views.LanguageModelRegistry.provider_for_dataset") as mock_provider,
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
                "agent.conversation.views.respond_to_user_message_task.apply_async",
                return_value=type("obj", (), {"id": "fake-task-id"}),
            ) as mock_task,
            patch("agent.conversation.views.LanguageModelRegistry.provider_for_dataset") as mock_provider,
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
                "agent.conversation.views.respond_to_user_message_task.apply_async",
                return_value=type("obj", (), {"id": "fake-task-id"}),
            ) as mock_task,
            patch("agent.conversation.views.LanguageModelRegistry.provider_for_dataset") as mock_provider,
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
                "agent.conversation.views.respond_to_user_message_task.apply_async",
                return_value=type("obj", (), {"id": "fake-task-id"}),
            ) as mock_task,
            patch("agent.conversation.views.LanguageModelRegistry.provider_for_dataset") as mock_provider,
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
