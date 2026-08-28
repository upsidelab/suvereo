import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.models import DatasetGroupRoleAssignment, DatasetRole, DatasetUserRoleAssignment
from account.tests.helpers import assign_role, client_for, grant, make_group, make_role
from account.tests.public_permission_codes_contract import (
    AGENT_VIEW,
    CONVERSATION_CONVERSE,
    DATASET_SCOPED_CONTRACT,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def role():
    return make_role("editor", PERMISSIONS.AGENT.VIEW, PERMISSIONS.AGENT.CHANGE)


@pytest.fixture
def list_url():
    return reverse("dataset_role_list")


@pytest.fixture
def detail_url(role):
    return reverse("dataset_role_details", args=[role.id])


class TestReadingRolesRequiresTheViewCode:
    def test_returns_401_when_unauthenticated(self, list_url):
        assert APIClient().get(list_url).status_code == status.HTTP_401_UNAUTHORIZED

    def test_a_global_dataset_role_view_holder_can_list(self, api_client, user, list_url, role):
        grant(user, PERMISSIONS.DATA_SET_ROLE.VIEW)

        response = api_client.get(list_url)

        assert response.status_code == status.HTTP_200_OK
        assert role.id in [row["id"] for row in response.data["results"]]

    def test_an_assign_holder_reaches_the_catalogue_through_the_view_code_it_requires(self, user, list_url, role):
        """An assigner has to see the catalogue to grant anything from it - `assign` never travels without `view`."""
        grant(user, PERMISSIONS.DATA_SET_ROLE.ASSIGN, PERMISSIONS.DATA_SET_ROLE.VIEW)

        response = client_for(user).get(list_url)

        assert response.status_code == status.HTTP_200_OK

    def test_a_user_holding_neither_is_denied(self, api_client, list_url, detail_url):
        assert api_client.get(list_url).status_code == status.HTTP_403_FORBIDDEN
        assert api_client.get(detail_url).status_code == status.HTTP_403_FORBIDDEN


class TestWritingDatasetRolesNeedsItsOwnLifecycleCode:
    @pytest.mark.parametrize(
        ("method", "uses_detail_url", "body", "code", "expected_status"),
        [
            ("post", False, {"name": "new-role"}, PERMISSIONS.DATA_SET_ROLE.ADD, status.HTTP_201_CREATED),
            (
                "patch",
                True,
                {"permissions": [AGENT_VIEW, CONVERSATION_CONVERSE]},
                PERMISSIONS.DATA_SET_ROLE.CHANGE,
                status.HTTP_200_OK,
            ),
            ("put", True, {"name": "renamed"}, PERMISSIONS.DATA_SET_ROLE.CHANGE, status.HTTP_200_OK),
            ("delete", True, None, PERMISSIONS.DATA_SET_ROLE.DELETE, status.HTTP_204_NO_CONTENT),
        ],
        ids=["create", "patch permissions", "rename", "delete"],
    )
    def test_a_holder_of_the_code_can_write(
        self, user, list_url, detail_url, role, method, uses_detail_url, body, code, expected_status
    ):
        grant(user, PERMISSIONS.DATA_SET_ROLE.VIEW, code)
        url = detail_url if uses_detail_url else list_url

        response = getattr(client_for(user), method)(url, body, format="json")

        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        ("method", "uses_detail_url", "body"),
        [
            ("post", False, {"name": "new-role"}),
            ("patch", True, {"permissions": [CONVERSATION_CONVERSE]}),
            ("put", True, {"name": "renamed"}),
            ("delete", True, None),
        ],
        ids=["create", "patch permissions", "rename", "delete"],
    )
    def test_reading_and_assigning_do_not_carry_the_write(
        self, user, list_url, detail_url, role, method, uses_detail_url, body
    ):
        grant(user, PERMISSIONS.DATA_SET_ROLE.VIEW, PERMISSIONS.DATA_SET_ROLE.ASSIGN)
        url = detail_url if uses_detail_url else list_url

        response = getattr(client_for(user), method)(url, body, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert DatasetRole.objects.filter(pk=role.pk).exists()
        assert not DatasetRole.objects.filter(name__in=["new-role", "renamed"]).exists()

    def test_an_admin_still_reaches_every_write(self, admin_api_client, list_url):
        response = admin_api_client.post(list_url, {"name": "new-role"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert DatasetRole.objects.filter(name="new-role").exists()

    def test_a_change_holder_can_widen_a_role_reaching_every_dataset_scoped_code(self, user, detail_url, role):
        grant(user, PERMISSIONS.DATA_SET_ROLE.VIEW, PERMISSIONS.DATA_SET_ROLE.CHANGE)

        response = client_for(user).patch(detail_url, {"permissions": list(DATASET_SCOPED_CONTRACT)}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert set(response.data["permissions"]) == set(DATASET_SCOPED_CONTRACT)


class TestDatasetRoleDeletion:
    def test_deleting_a_role_revokes_it_from_everyone_holding_it(
        self, admin_api_client, detail_url, role, user, data_set
    ):
        assign_role(user, data_set, role)
        assign_role(make_group("contractors"), data_set, role)

        response = admin_api_client.delete(detail_url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not DatasetRole.objects.filter(pk=role.pk).exists()
        assert not DatasetUserRoleAssignment.objects.filter(role_id=role.pk).exists()
        assert not DatasetGroupRoleAssignment.objects.filter(role_id=role.pk).exists()

    def test_an_unassigned_role_can_be_deleted(self, admin_api_client, detail_url, role):
        response = admin_api_client.delete(detail_url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not DatasetRole.objects.filter(pk=role.pk).exists()
