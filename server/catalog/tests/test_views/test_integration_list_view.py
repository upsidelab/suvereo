from unittest.mock import patch

import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.models import Integration
from catalog.tests.integration_mocks import MockMultiInstanceIntegration, MockSingleInstanceIntegration

pytestmark = pytest.mark.django_db


class TestIntegrationListViewPost:
    @pytest.fixture
    def url(self, data_set):
        return reverse("integration-list", kwargs={"data_set_id": data_set.pk})

    def test_post_unknown_type_returns_400(self, admin_api_client, url):
        response = admin_api_client.post(url, {"type": "does_not_exist", "config": {}}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not Integration.objects.exists()

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    @patch("catalog.integrations.views.sync_integration_task.delay")
    def test_post_creates_first_integration_of_capped_type(
        self, mock_sync, mock_get_plugin_class, admin_api_client, url, data_set
    ):
        mock_get_plugin_class.return_value = MockSingleInstanceIntegration

        response = admin_api_client.post(url, {"type": "mock_single", "config": {}}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert Integration.objects.filter(dataset=data_set, type="mock_single").count() == 1
        mock_sync.assert_called_once()

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    @patch("catalog.integrations.views.sync_integration_task.delay")
    def test_post_second_integration_of_capped_type_returns_400(
        self, mock_sync, mock_get_plugin_class, admin_api_client, url, data_set
    ):
        mock_get_plugin_class.return_value = MockSingleInstanceIntegration
        baker.make(Integration, dataset=data_set, type="mock_single", allows_multiple_instances=False)

        response = admin_api_client.post(url, {"type": "mock_single", "config": {}}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Integration.objects.filter(dataset=data_set, type="mock_single").count() == 1
        mock_sync.assert_not_called()

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    @patch("catalog.integrations.views.sync_integration_task.delay")
    def test_post_second_integration_of_multi_instance_type_succeeds(
        self, mock_sync, mock_get_plugin_class, admin_api_client, url, data_set
    ):
        mock_get_plugin_class.return_value = MockMultiInstanceIntegration
        baker.make(Integration, dataset=data_set, type="mock_multi", allows_multiple_instances=True)

        response = admin_api_client.post(url, {"type": "mock_multi", "config": {}}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert Integration.objects.filter(dataset=data_set, type="mock_multi").count() == 2
        mock_sync.assert_called_once()


class TestIntegrationListViewGet:
    @pytest.fixture
    def url(self, data_set):
        return reverse("integration-list", kwargs={"data_set_id": data_set.pk})

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_get_lists_all_instances_of_multi_instance_type(
        self, mock_get_plugin_class, admin_api_client, url, data_set
    ):
        mock_get_plugin_class.return_value = MockMultiInstanceIntegration
        baker.make(Integration, dataset=data_set, type="mock_multi", allows_multiple_instances=True, _quantity=2)

        response = admin_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2