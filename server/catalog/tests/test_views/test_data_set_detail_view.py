import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from account.authorization import PERMISSIONS
from account.models import DatasetGroupRoleAssignment, DatasetRole, DatasetUserRoleAssignment, UserGroup
from account.tests.helpers import grant
from account.tests.public_permission_codes_contract import (
    AGENT_VIEW,
    DATASET_SCOPED_CONTRACT,
    INTEGRATION_VIEW,
)
from catalog.models import DataSet

pytestmark = pytest.mark.django_db


def _permission(codename: str) -> Permission:
    app_label, name = codename.split(".")
    return Permission.objects.get(codename=name, content_type__app_label=app_label)


def _url(data_set):
    return reverse("data_set_detail", kwargs={"data_set_id": data_set.id})


class TestDataSetDetailViewGet:
    def test_outsider_cannot_view_dataset(self, api_client, data_set):
        # Obscured as 404, not 403 - a non-member shouldn't be able to tell this dataset
        # apart from one that doesn't exist.
        response = api_client.get(_url(data_set))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_direct_role_member_can_view_dataset(self, api_client, user, data_set):
        role = baker.make(DatasetRole)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=data_set, role=role)

        response = api_client.get(_url(data_set))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == data_set.id

    def test_global_role_member_can_view_dataset(self, api_client, user, data_set):
        group = baker.make(UserGroup)
        group.members.add(user)
        role = baker.make(DatasetRole)
        baker.make(DatasetGroupRoleAssignment, group=group, dataset=data_set, role=role)

        response = api_client.get(_url(data_set))

        assert response.status_code == status.HTTP_200_OK

    def test_global_view_dataset_holder_can_view_any_dataset(self, api_client, user, data_set):
        grant(user, PERMISSIONS.DATA_SET.VIEW)

        response = api_client.get(_url(data_set))

        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_view_any_dataset(self, admin_api_client, data_set):
        response = admin_api_client.get(_url(data_set))

        assert response.status_code == status.HTTP_200_OK

    def test_nonexistent_dataset_returns_404(self, api_client):
        url = reverse("data_set_detail", kwargs={"data_set_id": 9999})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_response_carries_the_members_codes_on_this_dataset(self, api_client, user, data_set):
        role = baker.make(DatasetRole)
        role.permissions.add(_permission(PERMISSIONS.AGENT.VIEW), _permission(PERMISSIONS.INTEGRATION.VIEW))
        baker.make(DatasetUserRoleAssignment, user=user, dataset=data_set, role=role)

        response = api_client.get(_url(data_set))

        assert response.data["permissions"] == [AGENT_VIEW, INTEGRATION_VIEW]

    def test_admin_response_carries_every_dataset_scoped_code(self, admin_api_client, data_set):
        response = admin_api_client.get(_url(data_set))

        assert set(response.data["permissions"]) == DATASET_SCOPED_CONTRACT


class TestDataSetDetailViewPatch:
    def test_outsider_cannot_update_dataset(self, api_client, data_set):
        response = api_client.patch(_url(data_set), {"name": "Renamed"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_plain_member_cannot_update_dataset(self, api_client, user, data_set):
        role = baker.make(DatasetRole)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=data_set, role=role)

        response = api_client.patch(_url(data_set), {"name": "Renamed"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_global_change_dataset_holder_can_update_dataset(self, api_client, user, data_set):
        grant(user, PERMISSIONS.DATA_SET.CHANGE)

        response = api_client.patch(_url(data_set), {"name": "Renamed"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        data_set.refresh_from_db()
        assert data_set.name == "Renamed"

    def test_admin_can_update_dataset(self, admin_api_client, data_set):
        response = admin_api_client.patch(_url(data_set), {"name": "Renamed"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        data_set.refresh_from_db()
        assert data_set.name == "Renamed"


class TestDataSetDetailViewDelete:
    def test_outsider_cannot_delete_dataset(self, api_client, data_set):
        response = api_client.delete(_url(data_set))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert DataSet.objects.filter(id=data_set.id).exists()

    def test_plain_member_cannot_delete_dataset(self, api_client, user, data_set):
        role = baker.make(DatasetRole)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=data_set, role=role)

        response = api_client.delete(_url(data_set))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert DataSet.objects.filter(id=data_set.id).exists()

    def test_global_delete_dataset_holder_can_delete_dataset(self, api_client, user, data_set):
        grant(user, PERMISSIONS.DATA_SET.DELETE)

        response = api_client.delete(_url(data_set))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not DataSet.objects.filter(id=data_set.id).exists()

    def test_admin_can_delete_dataset(self, admin_api_client, data_set):
        response = admin_api_client.delete(_url(data_set))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not DataSet.objects.filter(id=data_set.id).exists()
