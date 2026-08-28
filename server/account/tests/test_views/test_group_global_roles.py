import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from account.authorization import PERMISSIONS
from account.models import User
from account.tests.helpers import client_for, grant, join_group, make_global_role, make_group

pytestmark = pytest.mark.django_db


@pytest.fixture
def group():
    return make_group("contractors")


@pytest.fixture
def global_role():
    return make_global_role("user-managers", PERMISSIONS.USER.VIEW)


@pytest.fixture
def grants_url(group):
    return reverse("group_global_role_list", args=[group.id])


@pytest.fixture
def granter():
    return grant(
        baker.make(User, email="granter@example.com"),
        PERMISSIONS.GLOBAL_ROLE.VIEW,
        PERMISSIONS.GLOBAL_ROLE.ASSIGN,
        PERMISSIONS.GROUP.VIEW,
    )


def _grant_url(group, global_role) -> str:
    return reverse("group_global_role_details", args=[group.id, global_role.id])


class TestGrantingAGlobalRoleToAGroup:
    def test_a_global_role_assign_holder_can_grant_one(self, granter, group, global_role, grants_url):
        response = client_for(granter).post(grants_url, {"global_role_id": global_role.id}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data == {"id": global_role.id, "name": "user-managers", "description": ""}
        assert group.global_roles.filter(pk=global_role.pk).exists()

    def test_group_change_does_not_carry_it(self, user, group, global_role, grants_url):
        grant(user, PERMISSIONS.GROUP.VIEW, PERMISSIONS.GROUP.CHANGE, PERMISSIONS.GROUP.ASSIGN)

        response = client_for(user).post(grants_url, {"global_role_id": global_role.id}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not group.global_roles.exists()

    def test_a_plain_user_cannot_grant_anything(self, api_client, group, global_role, grants_url):
        response = api_client.post(grants_url, {"global_role_id": global_role.id}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not group.global_roles.exists()

    def test_granting_a_role_the_group_already_holds_reports_no_change(self, granter, group, global_role, grants_url):
        group.global_roles.add(global_role)

        response = client_for(granter).post(grants_url, {"global_role_id": global_role.id}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert group.global_roles.count() == 1

    @pytest.mark.parametrize(
        ("body", "expected_error"),
        [
            ({"global_role_id": 9999}, 'Invalid pk "9999" - object does not exist.'),
            ({}, "This field is required."),
        ],
        ids=["unknown global role", "missing body"],
    )
    def test_a_bad_body_is_rejected(self, granter, grants_url, body, expected_error):
        response = client_for(granter).post(grants_url, body, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert str(response.data["global_role_id"][0]) == expected_error

    def test_an_unknown_group_is_a_404(self, granter, global_role):
        response = client_for(granter).post(
            reverse("group_global_role_list", args=[9999]), {"global_role_id": global_role.id}, format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestRevokingAGlobalRoleFromAGroup:
    def test_a_global_role_assign_holder_can_revoke_one(self, granter, group, global_role):
        group.global_roles.add(global_role)

        response = client_for(granter).delete(_grant_url(group, global_role))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not group.global_roles.exists()

    def test_revoking_one_the_group_does_not_hold_reports_that_nothing_matched(self, granter, group, global_role):
        response = client_for(granter).delete(_grant_url(group, global_role))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "No global role grant matches the given query."

    def test_revoking_leaves_the_role_itself_alone(self, granter, group, global_role):
        """The grant goes, the role does not - other groups and members may still hold it."""
        group.global_roles.add(global_role)

        client_for(granter).delete(_grant_url(group, global_role))

        assert type(global_role).objects.filter(pk=global_role.pk).exists()

    def test_a_plain_user_cannot_revoke_anything(self, api_client, group, global_role):
        group.global_roles.add(global_role)

        response = api_client.delete(_grant_url(group, global_role))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert group.global_roles.exists()


class TestWhatTheGrantActuallyDoes:
    def test_the_role_s_permissions_reach_everyone_already_in_the_group(self, granter, group, global_role, grants_url):
        member = baker.make(User, email="member@example.com")
        join_group(member, group)

        assert client_for(member).get(reverse("user_list")).status_code == status.HTTP_403_FORBIDDEN

        client_for(granter).post(grants_url, {"global_role_id": global_role.id}, format="json")

        assert client_for(User.objects.get(pk=member.pk)).get(reverse("user_list")).status_code == status.HTTP_200_OK

    def test_revoking_takes_it_back_from_them(self, granter, group, global_role):
        member = baker.make(User, email="member@example.com")
        join_group(member, group)
        group.global_roles.add(global_role)

        client_for(granter).delete(_grant_url(group, global_role))

        assert (
            client_for(User.objects.get(pk=member.pk)).get(reverse("user_list")).status_code
            == status.HTTP_403_FORBIDDEN
        )

    def test_a_member_holding_the_role_directly_keeps_it_when_the_group_loses_it(self, granter, group, global_role):
        member = baker.make(User, email="member@example.com")
        join_group(member, group)
        group.global_roles.add(global_role)
        global_role.members.add(member)

        client_for(granter).delete(_grant_url(group, global_role))

        assert client_for(User.objects.get(pk=member.pk)).get(reverse("user_list")).status_code == status.HTTP_200_OK
