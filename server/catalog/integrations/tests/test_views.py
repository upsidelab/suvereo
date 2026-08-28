from unittest.mock import patch

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.models import DatasetRole, DatasetUserRoleAssignment
from catalog.models import DataSet, Integration

pytestmark = pytest.mark.django_db


class _DummyPlugin:
    TYPE = "dummy"
    NAME = "Dummy Integration"
    INTEGRATION_TYPE_NAME = "Dummy"
    CONFIGURATION_ARGS = None

    @classmethod
    def is_syncable(cls):
        return True

    def get_config_schema(self):
        return {}


def _permission(codename: str) -> Permission:
    app_label, name = codename.split(".")
    return Permission.objects.get(codename=name, content_type__app_label=app_label)


def _grant_dataset_permission(user, dataset, *codenames: str) -> DatasetRole:
    role = baker.make(DatasetRole)
    role.permissions.set([_permission(codename) for codename in codenames])
    baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)
    return role


class TestIntegrationTypeListView:
    def test_get_returns_401(self):
        response = APIClient().get(reverse("integration-types"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_outsider_with_no_add_or_change_integration_anywhere_is_denied(self, api_client):
        response = api_client.get(reverse("integration-types"))

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_dataset_member_holding_only_add_integration_is_allowed(self, api_client, user):
        data_set = baker.make(DataSet)
        _grant_dataset_permission(user, data_set, PERMISSIONS.INTEGRATION.ADD)

        with patch(
            "catalog.integrations.views.IntegrationPluginRegistry.get_plugin_classes",
            return_value=[_DummyPlugin],
        ):
            response = api_client.get(reverse("integration-types"))

        assert response.status_code == status.HTTP_200_OK

    def test_dataset_member_holding_only_change_integration_is_allowed(self, api_client, user):
        data_set = baker.make(DataSet)
        _grant_dataset_permission(user, data_set, PERMISSIONS.INTEGRATION.CHANGE)

        with patch(
            "catalog.integrations.views.IntegrationPluginRegistry.get_plugin_classes",
            return_value=[_DummyPlugin],
        ):
            response = api_client.get(reverse("integration-types"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]["type"] == "dummy"

    def test_dataset_member_holding_only_view_integration_is_denied(self, api_client, user):
        data_set = baker.make(DataSet)
        _grant_dataset_permission(user, data_set, PERMISSIONS.INTEGRATION.VIEW)

        response = api_client.get(reverse("integration-types"))

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_is_allowed(self, admin_api_client):
        with patch(
            "catalog.integrations.views.IntegrationPluginRegistry.get_plugin_classes",
            return_value=[_DummyPlugin],
        ):
            response = admin_api_client.get(reverse("integration-types"))

        assert response.status_code == status.HTTP_200_OK


class TestIntegrationListView:
    def _url(self, data_set):
        return reverse("integration-list", kwargs={"data_set_id": data_set.id})

    def test_get_outsider_gets_not_found(self, api_client, data_set):
        # Obscured as 404, not 403 - a non-member shouldn't be able to tell this dataset
        # apart from one that doesn't exist.
        response = api_client.get(self._url(data_set))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_outsider_gets_identical_404_body_to_a_nonexistent_dataset(self, api_client, data_set):
        # The two cases must be indistinguishable - not just the same status code, but the
        # same response body - or a non-member could tell them apart by comparing responses.
        existing_but_hidden = api_client.get(self._url(data_set))
        nonexistent = api_client.get(reverse("integration-list", kwargs={"data_set_id": 9999}))

        assert existing_but_hidden.data == {"detail": "No DataSet matches the given query."}
        assert existing_but_hidden.data == nonexistent.data

    def test_get_dataset_member_without_view_integration_gets_forbidden(self, api_client, user, data_set):
        _grant_dataset_permission(user, data_set)

        response = api_client.get(self._url(data_set))

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_lists_integrations(self, api_client, user, data_set):
        _grant_dataset_permission(user, data_set, PERMISSIONS.INTEGRATION.VIEW)
        integration = baker.make(Integration, dataset=data_set, type="dummy")

        with patch(
            "catalog.integrations.views.IntegrationPluginRegistry.get_plugin_class_by_type",
            return_value=_DummyPlugin,
        ):
            response = api_client.get(self._url(data_set))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == integration.id

    def test_dataset_not_found(self, api_client):
        response = api_client.get(reverse("integration-list", kwargs={"data_set_id": 9999}))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_post_outsider_gets_not_found(self, api_client, data_set):
        response = api_client.post(self._url(data_set), {"type": "dummy"}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_post_dataset_member_without_add_integration_gets_forbidden(self, api_client, user, data_set):
        _grant_dataset_permission(user, data_set)

        response = api_client.post(self._url(data_set), {"type": "dummy"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_post_creates_integration(self, api_client, user, data_set):
        _grant_dataset_permission(user, data_set, PERMISSIONS.INTEGRATION.ADD)

        with (
            patch(
                "catalog.integrations.views.IntegrationPluginRegistry.get_plugin_class_by_type",
                return_value=_DummyPlugin,
            ),
            patch("catalog.integrations.views.sync_integration_task.delay"),
        ):
            response = api_client.post(self._url(data_set), {"type": "dummy"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert Integration.objects.filter(dataset=data_set, type="dummy").exists()


class TestIntegrationUpdateDeleteView:
    @pytest.fixture
    def integration(self, data_set):
        return baker.make(Integration, dataset=data_set, type="dummy")

    def _url(self, data_set, integration):
        return reverse("integration-detail", kwargs={"data_set_id": data_set.id, "pk": integration.id})

    def test_patch_outsider_gets_not_found(self, api_client, data_set, integration):
        response = api_client.patch(self._url(data_set, integration), {"config": {}}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_dataset_member_without_change_integration_gets_forbidden(
        self, api_client, user, data_set, integration
    ):
        _grant_dataset_permission(user, data_set)

        response = api_client.patch(self._url(data_set, integration), {"config": {}}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_patch_updates_integration(self, api_client, user, data_set, integration):
        _grant_dataset_permission(user, data_set, PERMISSIONS.INTEGRATION.CHANGE)

        with patch(
            "catalog.integrations.views.IntegrationPluginRegistry.get_plugin_class_by_type",
            return_value=_DummyPlugin,
        ):
            response = api_client.patch(self._url(data_set, integration), {"config": {"a": 1}}, format="json")

        assert response.status_code == status.HTTP_200_OK
        integration.refresh_from_db()
        assert integration.config == {"a": 1}

    def test_delete_outsider_gets_not_found(self, api_client, data_set, integration):
        response = api_client.delete(self._url(data_set, integration))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_dataset_member_without_delete_integration_gets_forbidden(
        self, api_client, user, data_set, integration
    ):
        _grant_dataset_permission(user, data_set)

        response = api_client.delete(self._url(data_set, integration))

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_removes_integration(self, api_client, user, data_set, integration):
        _grant_dataset_permission(user, data_set, PERMISSIONS.INTEGRATION.DELETE)

        response = api_client.delete(self._url(data_set, integration))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Integration.objects.filter(pk=integration.id).exists()

    def test_nonexistent_integration_returns_404(self, api_client, user, data_set):
        _grant_dataset_permission(user, data_set, PERMISSIONS.INTEGRATION.CHANGE)
        url = reverse("integration-detail", kwargs={"data_set_id": data_set.id, "pk": 9999})

        response = api_client.patch(url, {"config": {}}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestIntegrationSyncView:
    @pytest.fixture
    def integration(self, data_set):
        return baker.make(Integration, dataset=data_set, type="dummy")

    def _url(self, data_set, integration):
        return reverse("integration-sync", kwargs={"data_set_id": data_set.id, "pk": integration.id})

    def test_outsider_gets_not_found(self, api_client, data_set, integration):
        response = api_client.post(self._url(data_set, integration))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_dataset_member_without_sync_integration_gets_forbidden(self, api_client, user, data_set, integration):
        _grant_dataset_permission(user, data_set)

        response = api_client.post(self._url(data_set, integration))

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_role_holding_crud_but_not_sync_cannot_trigger_sync(self, api_client, user, data_set, integration):
        _grant_dataset_permission(
            user,
            data_set,
            PERMISSIONS.INTEGRATION.VIEW,
            PERMISSIONS.INTEGRATION.ADD,
            PERMISSIONS.INTEGRATION.CHANGE,
            PERMISSIONS.INTEGRATION.DELETE,
        )

        response = api_client.post(self._url(data_set, integration))

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_role_holding_only_sync_can_trigger_sync(self, api_client, user, data_set, integration):
        _grant_dataset_permission(user, data_set, PERMISSIONS.INTEGRATION.SYNC)

        with patch("catalog.integrations.views.sync_integration_task.delay") as mock_delay:
            mock_delay.return_value.id = "task-id"
            response = api_client.post(self._url(data_set, integration))

        assert response.status_code == status.HTTP_202_ACCEPTED
        mock_delay.assert_called_once_with(integration.id)

    def test_role_holding_change_and_sync_can_do_both(self, api_client, user, data_set, integration):
        _grant_dataset_permission(user, data_set, PERMISSIONS.INTEGRATION.CHANGE, PERMISSIONS.INTEGRATION.SYNC)

        with patch("catalog.integrations.views.sync_integration_task.delay") as mock_delay:
            mock_delay.return_value.id = "task-id"
            sync_response = api_client.post(self._url(data_set, integration))
        with patch(
            "catalog.integrations.views.IntegrationPluginRegistry.get_plugin_class_by_type",
            return_value=_DummyPlugin,
        ):
            patch_response = api_client.patch(
                reverse("integration-detail", kwargs={"data_set_id": data_set.id, "pk": integration.id}),
                {"config": {"a": 1}},
                format="json",
            )

        assert sync_response.status_code == status.HTTP_202_ACCEPTED
        assert patch_response.status_code == status.HTTP_200_OK

    def test_nonexistent_integration_returns_404(self, api_client, user, data_set):
        _grant_dataset_permission(user, data_set, PERMISSIONS.INTEGRATION.SYNC)
        url = reverse("integration-sync", kwargs={"data_set_id": data_set.id, "pk": 9999})

        response = api_client.post(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_can_sync(self, admin_api_client, data_set, integration):
        with patch("catalog.integrations.views.sync_integration_task.delay") as mock_delay:
            mock_delay.return_value.id = "task-id"
            response = admin_api_client.post(self._url(data_set, integration))

        assert response.status_code == status.HTTP_202_ACCEPTED
