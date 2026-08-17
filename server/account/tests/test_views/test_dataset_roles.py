import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.models import DatasetRole
from account.tests.helpers import assign_role, client_for, grant, make_group, make_role
from account.tests.public_permission_codes_contract import CONVERSATION_CONVERSE

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


class TestReadingRolesAcceptsViewOrAssign:
    def test_returns_401_when_unauthenticated(self, list_url):
        assert APIClient().get(list_url).status_code == status.HTTP_401_UNAUTHORIZED

    def test_a_global_dataset_role_view_holder_can_list(self, api_client, user, list_url, role):
        grant(user, PERMISSIONS.DATASET_ROLE.VIEW)

        response = api_client.get(list_url)

        assert response.status_code == status.HTTP_200_OK
        assert role.id in [row["id"] for row in response.data["results"]]

    def test_an_assign_holder_on_a_single_data_set_can_list(self, user, list_url, data_set, role):
        """They have to see the catalogue to grant anything from it, and no role could carry
        `dataset_role.view` to say so."""
        assign_role(user, data_set, make_role("access-manager", PERMISSIONS.DATASET_ROLE.ASSIGN))

        response = client_for(user).get(list_url)

        assert response.status_code == status.HTTP_200_OK

    def test_a_user_holding_neither_is_denied(self, api_client, list_url, detail_url):
        assert api_client.get(list_url).status_code == status.HTTP_403_FORBIDDEN
        assert api_client.get(detail_url).status_code == status.HTTP_403_FORBIDDEN


class TestWritingRolesIsAdminOnly:
    @pytest.mark.parametrize(
        ("method", "uses_detail_url", "body"),
        [
            ("post", False, {"name": "new-role"}),
            ("patch", True, {"permissions": [CONVERSATION_CONVERSE]}),
            ("put", True, {"name": "renamed"}),
            ("delete", True, None),
        ],
    )
    def test_a_dataset_role_delegate_cannot_create_edit_or_delete_a_role(
        self, user, list_url, detail_url, role, data_set, method, uses_detail_url, body
    ):
        """Holding both dataset-role codes, globally, still is not enough: what a role *carries*
        is the ceiling on everything a delegate can hand out, so only an admin sets it."""
        grant(user, PERMISSIONS.DATASET_ROLE.VIEW)
        assign_role(user, data_set, make_role("access-manager", PERMISSIONS.DATASET_ROLE.ASSIGN))
        url = detail_url if uses_detail_url else list_url

        response = getattr(client_for(user), method)(url, body, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert DatasetRole.objects.filter(pk=role.pk).exists()
        assert not DatasetRole.objects.filter(name__in=["new-role", "renamed"]).exists()

    def test_an_admin_can_create_a_role(self, admin_api_client, list_url):
        response = admin_api_client.post(list_url, {"name": "new-role"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert DatasetRole.objects.filter(name="new-role").exists()


class TestDatasetRoleDeletion:
    def test_a_role_still_assigned_anywhere_cannot_be_deleted(self, admin_api_client, detail_url, role, user, data_set):
        assign_role(user, data_set, role)
        assign_role(make_group("support"), data_set, role)

        response = admin_api_client.delete(detail_url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["user_assignments"] == 1
        assert response.data["group_assignments"] == 1
        assert DatasetRole.objects.filter(pk=role.pk).exists()

    def test_an_unassigned_role_can_be_deleted(self, admin_api_client, detail_url, role):
        response = admin_api_client.delete(detail_url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not DatasetRole.objects.filter(pk=role.pk).exists()
