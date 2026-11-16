from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.tests.helpers import assign_role, make_role
from agent.conversation.tasks import TaskStatus

pytestmark = pytest.mark.django_db


class TestIntegrationSyncStatusView:
    @pytest.fixture
    def url(self):
        return reverse("integration-sync-status", kwargs={"task_id": "fake-task-id"})

    @staticmethod
    def _successful_result(data_set, task_type="integration_sync"):
        mock_result = MagicMock()
        mock_result.status = TaskStatus.SUCCESS
        mock_result.result = {
            "task_type": task_type,
            "integration_id": 7,
            "data_set_id": data_set.id,
            "synced": True,
        }
        return mock_result

    def test_get_status_unauthenticated_returns_401(self, url):
        response = APIClient().get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("utils.views.task_status.AsyncResult")
    def test_get_status_success_for_integration_viewer(self, mock_async_result, api_client, user, url, data_set):
        assign_role(user, data_set, make_role("integration-viewer", PERMISSIONS.INTEGRATION.VIEW))
        mock_async_result.return_value = self._successful_result(data_set)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == TaskStatus.SUCCESS
        assert response.data["result"]["integration_id"] == 7
        assert response.data["result"]["data_set_id"] == data_set.id
        assert response.data["result"]["synced"] is True

    @patch("utils.views.task_status.AsyncResult")
    def test_get_status_success_for_admin(self, mock_async_result, admin_api_client, url, data_set):
        mock_async_result.return_value = self._successful_result(data_set)

        response = admin_api_client.get(url)

        assert response.data["status"] == TaskStatus.SUCCESS
        assert response.data["result"]["synced"] is True

    @patch("utils.views.task_status.AsyncResult")
    def test_get_status_success_masked_without_integration_view(self, mock_async_result, api_client, url, data_set):
        mock_async_result.return_value = self._successful_result(data_set)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == TaskStatus.PENDING
        assert "result" not in response.data

    @patch("utils.views.task_status.AsyncResult")
    def test_get_status_success_masked_for_wrong_task_type(self, mock_async_result, admin_api_client, url, data_set):
        mock_async_result.return_value = self._successful_result(data_set, task_type="message_push")

        response = admin_api_client.get(url)

        assert response.data["status"] == TaskStatus.PENDING
        assert "result" not in response.data

    @patch("utils.views.task_status.AsyncResult")
    def test_get_status_failure(self, mock_async_result, api_client, url):
        mock_result = MagicMock()
        mock_result.status = TaskStatus.FAILURE
        mock_result.result = Exception("Sync failed")
        mock_async_result.return_value = mock_result

        response = api_client.get(url)

        assert response.data["status"] == TaskStatus.FAILURE
        assert "error" in response.data["result"]

    @patch("utils.views.task_status.AsyncResult")
    def test_get_status_pending(self, mock_async_result, api_client, url):
        mock_result = MagicMock()
        mock_result.status = TaskStatus.PENDING
        mock_result.result = None
        mock_async_result.return_value = mock_result

        response = api_client.get(url)

        assert response.data["status"] == TaskStatus.PENDING
