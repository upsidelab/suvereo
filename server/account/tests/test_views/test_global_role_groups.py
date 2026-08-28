import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.models import User
from account.tests.helpers import client_for, grant, join_group, make_global_role, make_group

pytestmark = pytest.mark.django_db


@pytest.fixture
def global_role():
    return make_global_role("user-managers", PERMISSIONS.USER.VIEW)


@pytest.fixture
def group():
    return make_group("contractors")


@pytest.fixture
def holders_url(global_role):
    return reverse("global_role_group_list", args=[global_role.id])


@pytest.fixture
def granter():
    return grant(
        baker.make(User, email="granter@example.com"),
        PERMISSIONS.GLOBAL_ROLE.VIEW,
        PERMISSIONS.GLOBAL_ROLE.ASSIGN,
        PERMISSIONS.GROUP.VIEW,
    )


def _holder_url(global_role, group) -> str:
    return reverse("global_role_group_details", args=[global_role.id, group.id])


class TestWhoCanReadAndWriteTheHolders:
    def test_returns_401_when_unauthenticated(self, holders_url):
        assert APIClient().get(holders_url).status_code == status.HTTP_401_UNAUTHORIZED

    def test_listing_needs_global_role_view(self, holders_url):
        outsider = baker.make(User, email="outsider@example.com")

        assert client_for(outsider).get(holders_url).status_code == status.HTTP_403_FORBIDDEN

    def test_granting_needs_global_role_assign(self, holders_url, group):
        viewer = grant(baker.make(User, email="viewer@example.com"), PERMISSIONS.GLOBAL_ROLE.VIEW)

        response = client_for(viewer).post(holders_url, {"group_id": group.id}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_revoking_needs_global_role_assign(self, global_role, group):
        viewer = grant(baker.make(User, email="viewer@example.com"), PERMISSIONS.GLOBAL_ROLE.VIEW)
        group.global_roles.add(global_role)

        response = client_for(viewer).delete(_holder_url(global_role, group))

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestTheHoldersListing:
    def test_reports_the_groups_holding_the_role_with_their_counts(self, granter, holders_url, global_role, group):
        join_group(baker.make(User, email="member@example.com"), group)
        group.global_roles.add(global_role)

        response = client_for(granter).get(holders_url)

        assert response.status_code == status.HTTP_200_OK
        assert [row["name"] for row in response.data] == ["contractors"]
        assert response.data[0]["member_count"] == 1
        assert response.data[0]["global_role_count"] == 1

    def test_a_group_holding_a_different_role_is_not_listed(self, granter, holders_url, group):
        group.global_roles.add(make_global_role("other", PERMISSIONS.AGENT.VIEW))

        assert client_for(granter).get(holders_url).data == []


class TestGrantingAndRevoking:
    def test_granting_reaches_the_groups_members(self, granter, holders_url, global_role, group):
        member = baker.make(User, email="member@example.com")
        join_group(member, group)

        response = client_for(granter).post(holders_url, {"group_id": group.id}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.get(pk=member.pk).has_perm(PERMISSIONS.USER.VIEW)

    def test_granting_twice_reports_no_change(self, granter, holders_url, global_role, group):
        client = client_for(granter)
        client.post(holders_url, {"group_id": group.id}, format="json")

        response = client.post(holders_url, {"group_id": group.id}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert group.global_roles.count() == 1

    def test_the_same_grant_is_visible_from_the_group_side(self, granter, holders_url, global_role, group):
        client_for(granter).post(holders_url, {"group_id": group.id}, format="json")

        from_group_side = client_for(granter).get(reverse("group_details", args=[group.id]))

        assert [row["id"] for row in from_group_side.data["global_roles"]] == [global_role.id]

    def test_revoking_takes_the_permission_back(self, granter, global_role, group):
        member = baker.make(User, email="member@example.com")
        join_group(member, group)
        group.global_roles.add(global_role)

        response = client_for(granter).delete(_holder_url(global_role, group))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.get(pk=member.pk).has_perm(PERMISSIONS.USER.VIEW)

    def test_revoking_a_grant_that_does_not_exist_is_a_404(self, granter, global_role, group):
        response = client_for(granter).delete(_holder_url(global_role, group))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_an_unknown_group_in_the_body_is_a_400(self, granter, holders_url):
        response = client_for(granter).post(holders_url, {"group_id": 9999}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
