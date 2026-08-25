import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.models import DatasetGlobalRoleAssignment, GlobalRole
from account.tests.helpers import assign_role, client_for, grant, make_role, permission
from account.tests.public_permission_codes_contract import DATASET_VIEW, USER_VIEW

pytestmark = pytest.mark.django_db


@pytest.fixture
def global_role():
    global_role = GlobalRole.objects.create(name="support")
    global_role.permissions.add(permission(PERMISSIONS.DATASET.VIEW))
    return global_role


@pytest.fixture
def list_url():
    return reverse("global_role_list")


@pytest.fixture
def detail_url(global_role):
    return reverse("global_role_details", args=[global_role.id])


class TestReadingGroupsRequiresGroupView:
    def test_returns_401_when_unauthenticated(self, list_url, detail_url):
        assert APIClient().get(list_url).status_code == status.HTTP_401_UNAUTHORIZED
        assert APIClient().get(detail_url).status_code == status.HTTP_401_UNAUTHORIZED

    def test_a_group_view_holder_can_list_and_retrieve(self, api_client, user, list_url, detail_url):
        grant(user, PERMISSIONS.GLOBAL_ROLE.VIEW)

        assert api_client.get(list_url).status_code == status.HTTP_200_OK
        assert api_client.get(detail_url).status_code == status.HTTP_200_OK

    def test_group_assign_alone_does_not_substitute_for_group_view(self, api_client, user, list_url, detail_url):
        grant(user, PERMISSIONS.GLOBAL_ROLE.ASSIGN)

        assert api_client.get(list_url).status_code == status.HTTP_403_FORBIDDEN
        assert api_client.get(detail_url).status_code == status.HTTP_403_FORBIDDEN

    def test_a_user_holding_neither_is_denied(self, api_client, list_url, detail_url):
        assert api_client.get(list_url).status_code == status.HTTP_403_FORBIDDEN
        assert api_client.get(detail_url).status_code == status.HTTP_403_FORBIDDEN


class TestWritingGroupsIsAdminOnly:
    @pytest.mark.parametrize(
        "delegated",
        [(PERMISSIONS.GLOBAL_ROLE.VIEW,), (PERMISSIONS.GLOBAL_ROLE.ASSIGN, PERMISSIONS.GLOBAL_ROLE.VIEW)],
        ids=["viewer", "assigner"],
    )
    @pytest.mark.parametrize(
        ("method", "uses_detail_url", "body"),
        [
            ("post", False, {"name": "new-team"}),
            ("patch", True, {"permissions": [USER_VIEW]}),
            ("put", True, {"name": "renamed"}),
            ("delete", True, None),
        ],
    )
    def test_a_delegate_cannot_create_edit_or_delete_a_group(
        self, user, list_url, detail_url, global_role, delegated, method, uses_detail_url, body
    ):
        grant(user, *delegated)
        url = detail_url if uses_detail_url else list_url

        response = getattr(client_for(user), method)(url, body, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert GlobalRole.objects.filter(pk=global_role.pk).exists()
        assert not GlobalRole.objects.filter(name__in=["new-team", "renamed"]).exists()

    def test_an_admin_can_create_a_group(self, admin_api_client, list_url):
        response = admin_api_client.post(list_url, {"name": "new-team"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert GlobalRole.objects.filter(name="new-team").exists()


class TestGroupPayloads:
    def test_the_listing_carries_only_an_id_and_a_name(self, api_client, user, list_url, global_role):
        grant(user, PERMISSIONS.GLOBAL_ROLE.VIEW)

        response = api_client.get(list_url)

        assert [set(row) for row in response.data["results"]] == [{"id", "name"}]

    def test_the_detail_carries_permissions_as_public_codes(self, api_client, user, detail_url):
        grant(user, PERMISSIONS.GLOBAL_ROLE.VIEW)

        response = api_client.get(detail_url)

        assert response.data["permissions"] == [DATASET_VIEW]


class TestGlobalRoleDeletion:
    def test_deleting_a_global_role_gives_up_the_roles_it_held(self, admin_api_client, detail_url, global_role, data_set):
        assign_role(global_role, data_set, make_role("reader", PERMISSIONS.AGENT.VIEW))

        response = admin_api_client.delete(detail_url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not GlobalRole.objects.filter(pk=global_role.pk).exists()
        assert not DatasetGlobalRoleAssignment.objects.filter(global_role_id=global_role.pk).exists()

    def test_a_global_role_with_members_can_be_deleted(self, admin_api_client, detail_url, global_role, user):
        global_role.members.add(user)

        response = admin_api_client.delete(detail_url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not GlobalRole.objects.filter(pk=global_role.pk).exists()
