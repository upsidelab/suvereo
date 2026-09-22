from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.tests.helpers import assign_role, make_role
from agent.conversation.tasks import TaskStatus
from agent.models import Conversation

pytestmark = pytest.mark.django_db


class TestFileUploadStatusView:
    @pytest.fixture
    def url(self):
        return reverse("file-upload-status", kwargs={"task_id": "fake-task-id"})

    def test_get_status_unauthenticated_returns_401(self, url):
        client = APIClient()

        response = client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("agent.task_status.views.AsyncResult")
    def test_get_status_success_for_owner(self, mock_async_result, api_client, url, conversation):
        mock_result = MagicMock()
        mock_result.status = TaskStatus.SUCCESS
        mock_result.result = {
            "task_type": "file_upload",
            "status": TaskStatus.SUCCESS,
            "conversation_id": conversation.id,
            "file_id": 123,
            "uploaded_file": {
                "id": 123,
                "filename": "test.txt",
                "file_url": "/media/conversations/1/test.txt",
                "content_type": "text/plain",
            },
        }
        mock_async_result.return_value = mock_result

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["task_id"] == "fake-task-id"
        assert response.data["status"] == TaskStatus.SUCCESS
        assert response.data["result"]["file_id"] == 123
        assert response.data["result"]["uploaded_file"]["filename"] == "test.txt"

    @patch("agent.task_status.views.AsyncResult")
    def test_get_status_success_for_view_all_holder(self, mock_async_result, api_client, user, url):
        someone_elses_conversation = baker.make(Conversation)
        assign_role(
            user,
            someone_elses_conversation.data_set,
            make_role("view-all", PERMISSIONS.CONVERSATION.VIEW_ALL),
        )
        mock_result = MagicMock()
        mock_result.status = TaskStatus.SUCCESS
        mock_result.result = {
            "task_type": "file_upload",
            "status": TaskStatus.SUCCESS,
            "conversation_id": someone_elses_conversation.id,
            "file_id": 123,
        }
        mock_async_result.return_value = mock_result

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == TaskStatus.SUCCESS
        assert response.data["result"]["file_id"] == 123

    @patch("agent.task_status.views.AsyncResult")
    def test_get_status_success_masked_for_non_owner(self, mock_async_result, api_client, url):
        someone_elses_conversation = baker.make(Conversation)
        mock_result = MagicMock()
        mock_result.status = TaskStatus.SUCCESS
        mock_result.result = {
            "task_type": "file_upload",
            "status": TaskStatus.SUCCESS,
            "conversation_id": someone_elses_conversation.id,
            "file_id": 123,
        }
        mock_async_result.return_value = mock_result

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == TaskStatus.PENDING
        assert "result" not in response.data

    @patch("agent.task_status.views.AsyncResult")
    def test_get_status_success_masked_for_wrong_task_type(self, mock_async_result, api_client, url, conversation):
        mock_result = MagicMock()
        mock_result.status = TaskStatus.SUCCESS
        mock_result.result = {
            "task_type": "message_push",
            "conversation_id": conversation.id,
            "message_id": 42,
        }
        mock_async_result.return_value = mock_result

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == TaskStatus.PENDING
        assert "result" not in response.data

    @patch("agent.task_status.views.AsyncResult")
    def test_get_status_success_masked_for_unrecognised_result_shape(self, mock_async_result, api_client, url):
        mock_result = MagicMock()
        mock_result.status = TaskStatus.SUCCESS
        mock_result.result = "not-a-dict"
        mock_async_result.return_value = mock_result

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == TaskStatus.PENDING
        assert "result" not in response.data

    @patch("agent.task_status.views.AsyncResult")
    def test_get_status_failure(self, mock_async_result, api_client, url):
        mock_result = MagicMock()
        mock_result.status = TaskStatus.FAILURE
        mock_result.result = Exception("Processing failed")
        mock_async_result.return_value = mock_result

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["task_id"] == "fake-task-id"
        assert response.data["status"] == TaskStatus.FAILURE
        assert "error" in response.data["result"]

    @patch("agent.task_status.views.AsyncResult")
    def test_get_status_pending(self, mock_async_result, api_client, url):
        mock_result = MagicMock()
        mock_result.status = TaskStatus.PENDING
        mock_result.result = None
        mock_async_result.return_value = mock_result

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["task_id"] == "fake-task-id"
        assert response.data["status"] == TaskStatus.PENDING

    @patch("agent.task_status.views.AsyncResult")
    def test_get_status_exception_returns_500(self, mock_async_result, api_client, url):
        mock_async_result.side_effect = Exception("Celery error")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.data
        assert "Failed to get task status" in response.data["error"]


class TestMessagePushStatusView:
    @pytest.fixture
    def url(self):
        return reverse("message-push-status", kwargs={"task_id": "fake-task-id"})

    def test_get_status_unauthenticated_returns_401(self, url):
        client = APIClient()

        response = client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("agent.task_status.views.AsyncResult")
    def test_get_status_success_for_owner(self, mock_async_result, api_client, url, conversation):
        mock_result = MagicMock()
        mock_result.status = TaskStatus.SUCCESS
        mock_result.result = {"task_type": "message_push", "conversation_id": conversation.id, "message_id": 123}
        mock_async_result.return_value = mock_result

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["task_id"] == "fake-task-id"
        assert response.data["status"] == TaskStatus.SUCCESS
        assert response.data["result"]["conversation_id"] == conversation.id
        assert response.data["result"]["message_id"] == 123

    @patch("agent.task_status.views.AsyncResult")
    def test_get_status_success_for_view_all_holder(self, mock_async_result, api_client, user, url):
        someone_elses_conversation = baker.make(Conversation)
        assign_role(
            user,
            someone_elses_conversation.data_set,
            make_role("view-all", PERMISSIONS.CONVERSATION.VIEW_ALL),
        )
        mock_result = MagicMock()
        mock_result.status = TaskStatus.SUCCESS
        mock_result.result = {
            "task_type": "message_push",
            "conversation_id": someone_elses_conversation.id,
            "message_id": 123,
        }
        mock_async_result.return_value = mock_result

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == TaskStatus.SUCCESS
        assert response.data["result"]["message_id"] == 123

    @patch("agent.task_status.views.AsyncResult")
    def test_get_status_success_masked_for_non_owner(self, mock_async_result, api_client, url):
        someone_elses_conversation = baker.make(Conversation)
        mock_result = MagicMock()
        mock_result.status = TaskStatus.SUCCESS
        mock_result.result = {
            "task_type": "message_push",
            "conversation_id": someone_elses_conversation.id,
            "message_id": 123,
        }
        mock_async_result.return_value = mock_result

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == TaskStatus.PENDING
        assert "result" not in response.data

    @patch("agent.task_status.views.AsyncResult")
    def test_get_status_success_masked_for_wrong_task_type(self, mock_async_result, api_client, url, conversation):
        mock_result = MagicMock()
        mock_result.status = TaskStatus.SUCCESS
        mock_result.result = {"task_type": "file_upload", "conversation_id": conversation.id, "file_id": 5}
        mock_async_result.return_value = mock_result

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == TaskStatus.PENDING
        assert "result" not in response.data

    @patch("agent.task_status.views.AsyncResult")
    def test_get_status_failure(self, mock_async_result, api_client, url):
        mock_result = MagicMock()
        mock_result.status = TaskStatus.FAILURE
        mock_result.result = Exception("Processing failed")
        mock_async_result.return_value = mock_result

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["task_id"] == "fake-task-id"
        assert response.data["status"] == TaskStatus.FAILURE
        assert "error" in response.data["result"]

    @patch("agent.task_status.views.AsyncResult")
    def test_get_status_pending(self, mock_async_result, api_client, url):
        mock_result = MagicMock()
        mock_result.status = TaskStatus.PENDING
        mock_result.result = None
        mock_async_result.return_value = mock_result

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["task_id"] == "fake-task-id"
        assert response.data["status"] == TaskStatus.PENDING

    @patch("agent.task_status.views.AsyncResult")
    def test_get_status_exception_returns_500(self, mock_async_result, api_client, url):
        mock_async_result.side_effect = Exception("Celery error")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.data
        assert "Failed to get task status" in response.data["error"]
