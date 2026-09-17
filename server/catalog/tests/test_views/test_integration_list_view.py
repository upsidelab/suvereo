from unittest.mock import patch

import pytest
from django.db import IntegrityError
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.models import Integration
from catalog.serializers import IntegrationSerializer
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
    def test_post_config_that_fails_plugin_validation_returns_400(
        self, mock_sync, mock_get_plugin_class, admin_api_client, url
    ):
        """A config the plugin cannot load is rejected on write, not silently skipped at build time."""
        mock_get_plugin_class.return_value = MockMultiInstanceIntegration

        response = admin_api_client.post(
            url, {"type": "mock_multi", "config": {"marker": {"not": "a string"}}}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "marker" in response.data["config"]
        assert not Integration.objects.exists()
        mock_sync.assert_not_called()

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

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_post_does_not_report_an_unrelated_integrity_error_as_a_duplicate(
        self, mock_get_plugin_class, admin_api_client, url
    ):
        """Only the uniqueness constraint means 'already configured' — other failures must surface."""
        mock_get_plugin_class.return_value = MockSingleInstanceIntegration

        with patch.object(IntegrationSerializer, "save", side_effect=IntegrityError("null value in column violates")):
            with pytest.raises(IntegrityError):
                admin_api_client.post(url, {"type": "mock_single", "config": {}}, format="json")


class TestIntegrationUpdateView:
    @pytest.fixture
    def integration(self, data_set):
        return baker.make(
            Integration,
            dataset=data_set,
            type="mock_multi",
            allows_multiple_instances=True,
            config={"marker": "original"},
        )

    def _url(self, data_set, integration):
        return reverse("integration-detail", kwargs={"data_set_id": data_set.pk, "pk": integration.pk})

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_patch_config_that_fails_plugin_validation_returns_400(
        self, mock_get_plugin_class, admin_api_client, data_set, integration
    ):
        mock_get_plugin_class.return_value = MockMultiInstanceIntegration

        response = admin_api_client.patch(
            self._url(data_set, integration), {"config": {"marker": {"not": "a string"}}}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        integration.refresh_from_db()
        assert integration.config == {"marker": "original"}

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_patch_valid_config_is_stored(self, mock_get_plugin_class, admin_api_client, data_set, integration):
        mock_get_plugin_class.return_value = MockMultiInstanceIntegration

        response = admin_api_client.patch(
            self._url(data_set, integration), {"config": {"marker": "updated"}}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        integration.refresh_from_db()
        assert integration.config == {"marker": "updated"}


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

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_get_names_each_instance_by_its_own_config(self, mock_get_plugin_class, admin_api_client, url, data_set):
        """Several integrations of one type have to be tellable apart in the list."""
        mock_get_plugin_class.return_value = MockMultiInstanceIntegration
        kwargs = dict(dataset=data_set, type="mock_multi", allows_multiple_instances=True)
        baker.make(Integration, **kwargs, config={"marker": "first"})
        baker.make(Integration, **kwargs, config={"marker": "second"})

        response = admin_api_client.get(url)

        assert {row["name"] for row in response.data} == {
            "Mock Multi Instance (first)",
            "Mock Multi Instance (second)",
        }

    @patch.object(IntegrationPluginRegistry, "get_plugin_class_by_type")
    def test_get_falls_back_to_the_type_name_when_config_cannot_be_loaded(
        self, mock_get_plugin_class, admin_api_client, url, data_set
    ):
        """A record too broken to instantiate still has to list, just without its own label."""
        mock_get_plugin_class.return_value = MockMultiInstanceIntegration
        baker.make(
            Integration,
            dataset=data_set,
            type="mock_multi",
            allows_multiple_instances=True,
            config={"marker": {"not": "a string"}},
        )

        response = admin_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]["name"] == "Mock Multi Instance"
