import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.models import DatasetGlobalRoleAssignment, GlobalRole, User
from account.tests.helpers import assign_role, client_for, grant, make_role, permission
from account.tests.public_permission_codes_contract import (
    DATASET_VIEW,
    GLOBAL_ROLE_CHANGE,
    GLOBAL_ROLE_VIEW,
    USER_VIEW,
)

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


class TestWritingGlobalRolesNeedsItsOwnLifecycleCode:

    @pytest.mark.parametrize(
        ("method", "uses_detail_url", "body", "code", "expected_status"),
        [
            ("post", False, {"name": "new-team"}, PERMISSIONS.GLOBAL_ROLE.ADD, status.HTTP_201_CREATED),
            ("patch", True, {"permissions": [USER_VIEW]}, PERMISSIONS.GLOBAL_ROLE.CHANGE, status.HTTP_200_OK),
            ("put", True, {"name": "renamed"}, PERMISSIONS.GLOBAL_ROLE.CHANGE, status.HTTP_200_OK),
            ("delete", True, None, PERMISSIONS.GLOBAL_ROLE.DELETE, status.HTTP_204_NO_CONTENT),
        ],
        ids=["create", "patch permissions", "rename", "delete"],
    )
    def test_a_holder_of_the_code_can_write(
        self, user, list_url, detail_url, global_role, method, uses_detail_url, body, code, expected_status
    ):
        grant(user, PERMISSIONS.GLOBAL_ROLE.VIEW, code)
        url = detail_url if uses_detail_url else list_url

        response = getattr(client_for(user), method)(url, body, format="json")

        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        ("method", "uses_detail_url", "body"),
        [
            ("post", False, {"name": "new-team"}),
            ("patch", True, {"permissions": [USER_VIEW]}),
            ("put", True, {"name": "renamed"}),
            ("delete", True, None),
        ],
        ids=["create", "patch permissions", "rename", "delete"],
    )
    def test_reading_and_assigning_do_not_carry_the_write(
        self, user, list_url, detail_url, global_role, method, uses_detail_url, body
    ):
        grant(user, PERMISSIONS.GLOBAL_ROLE.VIEW, PERMISSIONS.GLOBAL_ROLE.ASSIGN)
        url = detail_url if uses_detail_url else list_url

        response = getattr(client_for(user), method)(url, body, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert GlobalRole.objects.filter(pk=global_role.pk).exists()
        assert not GlobalRole.objects.filter(name__in=["new-team", "renamed"]).exists()

    def test_an_admin_still_reaches_every_write(self, admin_api_client, list_url):
        response = admin_api_client.post(list_url, {"name": "new-team"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert GlobalRole.objects.filter(name="new-team").exists()


class TestGlobalRoleChangeIsSelfPromotion:
    def test_a_change_holder_can_widen_the_role_they_hold_it_through(self, user):
        grant(user, PERMISSIONS.GLOBAL_ROLE.VIEW, PERMISSIONS.GLOBAL_ROLE.CHANGE)
        own_role = GlobalRole.objects.get(members=user)

        response = client_for(user).patch(
            reverse("global_role_details", args=[own_role.id]),
            {"permissions": [GLOBAL_ROLE_VIEW, GLOBAL_ROLE_CHANGE, DATASET_VIEW]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert User.objects.get(pk=user.pk).has_perm(PERMISSIONS.DATASET.VIEW)


class TestGroupPayloads:
    def test_the_listing_carries_only_an_id_and_a_name(self, api_client, user, list_url, global_role):
        grant(user, PERMISSIONS.GLOBAL_ROLE.VIEW)

        response = api_client.get(list_url)

        assert response.data["results"]
        assert all(set(row) == {"id", "name"} for row in response.data["results"])

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
