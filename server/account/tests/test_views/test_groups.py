import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.tests.helpers import assign_role, client_for, grant, make_role, permission
from account.tests.public_permission_codes_contract import DATASET_VIEW, USER_VIEW

pytestmark = pytest.mark.django_db


@pytest.fixture
def group():
    group = Group.objects.create(name="support")
    group.permissions.add(permission(PERMISSIONS.DATASET.VIEW))
    return group


@pytest.fixture
def list_url():
    return reverse("group_list")


@pytest.fixture
def detail_url(group):
    return reverse("group_details", args=[group.id])


class TestReadingGroupsRequiresGroupView:
    def test_returns_401_when_unauthenticated(self, list_url, detail_url):
        assert APIClient().get(list_url).status_code == status.HTTP_401_UNAUTHORIZED
        assert APIClient().get(detail_url).status_code == status.HTTP_401_UNAUTHORIZED

    def test_a_group_view_holder_can_list_and_retrieve(self, api_client, user, list_url, detail_url):
        grant(user, PERMISSIONS.GROUP.VIEW)

        assert api_client.get(list_url).status_code == status.HTTP_200_OK
        assert api_client.get(detail_url).status_code == status.HTTP_200_OK

    def test_group_assign_alone_does_not_substitute_for_group_view(self, api_client, user, list_url, detail_url):
        grant(user, PERMISSIONS.GROUP.ASSIGN)

        assert api_client.get(list_url).status_code == status.HTTP_403_FORBIDDEN
        assert api_client.get(detail_url).status_code == status.HTTP_403_FORBIDDEN

    def test_a_user_holding_neither_is_denied(self, api_client, list_url, detail_url):
        assert api_client.get(list_url).status_code == status.HTTP_403_FORBIDDEN
        assert api_client.get(detail_url).status_code == status.HTTP_403_FORBIDDEN


class TestWritingGroupsIsAdminOnly:
    @pytest.mark.parametrize(
        "delegated",
        [(PERMISSIONS.GROUP.VIEW,), (PERMISSIONS.GROUP.ASSIGN, PERMISSIONS.GROUP.VIEW)],
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
        self, user, list_url, detail_url, group, delegated, method, uses_detail_url, body
    ):
        grant(user, *delegated)
        url = detail_url if uses_detail_url else list_url

        response = getattr(client_for(user), method)(url, body, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Group.objects.filter(pk=group.pk).exists()
        assert not Group.objects.filter(name__in=["new-team", "renamed"]).exists()

    def test_an_admin_can_create_a_group(self, admin_api_client, list_url):
        response = admin_api_client.post(list_url, {"name": "new-team"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert Group.objects.filter(name="new-team").exists()


class TestGroupPayloads:
    def test_the_listing_carries_only_an_id_and_a_name(self, api_client, user, list_url, group):
        grant(user, PERMISSIONS.GROUP.VIEW)

        response = api_client.get(list_url)

        assert [set(row) for row in response.data["results"]] == [{"id", "name"}]

    def test_the_detail_carries_permissions_as_public_codes(self, api_client, user, detail_url):
        grant(user, PERMISSIONS.GROUP.VIEW)

        response = api_client.get(detail_url)

        assert response.data["permissions"] == [DATASET_VIEW]


class TestGroupDeletion:
    def test_a_group_still_holding_a_role_on_a_data_set_cannot_be_deleted(
        self, admin_api_client, detail_url, group, data_set
    ):
        assign_role(group, data_set, make_role("reader", PERMISSIONS.AGENT.VIEW))

        response = admin_api_client.delete(detail_url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["dataset_assignments"] == 1
        assert Group.objects.filter(pk=group.pk).exists()

    def test_a_group_with_members_but_no_dataset_role_can_be_deleted(self, admin_api_client, detail_url, group, user):
        user.groups.add(group)

        response = admin_api_client.delete(detail_url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Group.objects.filter(pk=group.pk).exists()
