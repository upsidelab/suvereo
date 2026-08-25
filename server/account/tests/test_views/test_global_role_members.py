import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.models import GlobalRole, User
from account.tests.helpers import client_for, grant, make_global_role

pytestmark = pytest.mark.django_db


@pytest.fixture
def global_role():
    return GlobalRole.objects.create(name="support")


@pytest.fixture
def members_url(global_role):
    return reverse("global_role_member_list", args=[global_role.id])


@pytest.fixture
def member():
    return baker.make(User, email="member@example.com")


@pytest.fixture
def assigner():
    return grant(baker.make(User, email="assigner@example.com"), PERMISSIONS.GLOBAL_ROLE.VIEW, PERMISSIONS.GLOBAL_ROLE.ASSIGN)


def _member_url(global_role, user) -> str:
    return reverse("global_role_member_details", args=[global_role.id, user.id])


class TestListingMembers:
    def test_returns_401_when_unauthenticated(self, members_url):
        assert APIClient().get(members_url).status_code == status.HTTP_401_UNAUTHORIZED

    def test_a_group_view_holder_sees_the_members_ordered_by_email(self, api_client, user, global_role, members_url):
        grant(user, PERMISSIONS.GLOBAL_ROLE.VIEW)
        for email in ["carol@example.com", "alice@example.com", "bob@example.com"]:
            global_role.members.add(baker.make(User, email=email))

        response = api_client.get(members_url)

        assert response.status_code == status.HTTP_200_OK
        assert [row["email"] for row in response.data] == [
            "alice@example.com",
            "bob@example.com",
            "carol@example.com",
        ]

    def test_a_user_without_group_view_is_denied(self, api_client, members_url):
        assert api_client.get(members_url).status_code == status.HTTP_403_FORBIDDEN


class TestAddingAMember:
    def test_an_assigner_can_add_a_user(self, assigner, member, global_role, members_url):
        response = client_for(assigner).post(members_url, {"user_id": member.id}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert global_role.members.filter(pk=member.pk).exists()

    def test_a_plain_user_cannot_add_anyone(self, api_client, member, global_role, members_url):
        response = api_client.post(members_url, {"user_id": member.id}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not global_role.members.filter(pk=member.pk).exists()

    def test_adding_someone_who_is_already_a_member_reports_no_change(self, assigner, member, global_role, members_url):
        """`200`, not a second `201`. The membership is a set, and the caller is told the request
        was a no-op rather than being led to believe it created something."""
        global_role.members.add(member)

        response = client_for(assigner).post(members_url, {"user_id": member.id}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert global_role.members.filter(pk=member.pk).count() == 1

    def test_a_service_account_can_be_added(self, assigner, global_role, members_url):
        service_account = baker.make(User, email="bot@example.com", is_service_account=True)

        response = client_for(assigner).post(members_url, {"user_id": service_account.id}, format="json")

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.parametrize(
        ("body", "expected_status", "expected_error"),
        [
            ({"user_id": 9999}, status.HTTP_400_BAD_REQUEST, 'Invalid pk "9999" - object does not exist.'),
            ({}, status.HTTP_400_BAD_REQUEST, "This field is required."),
        ],
        ids=["unknown user", "missing body"],
    )
    def test_a_bad_body_is_rejected(self, assigner, members_url, body, expected_status, expected_error):
        response = client_for(assigner).post(members_url, body, format="json")

        assert response.status_code == expected_status
        assert str(response.data["user_id"][0]) == expected_error

    def test_an_unknown_group_is_a_404(self, assigner, member):
        response = client_for(assigner).post(
            reverse("global_role_member_list", args=[9999]), {"user_id": member.id}, format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestRemovingAMember:
    def test_an_assigner_can_remove_a_member(self, assigner, member, global_role):
        global_role.members.add(member)

        response = client_for(assigner).delete(_member_url(global_role, member))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not global_role.members.filter(pk=member.pk).exists()

    def test_removing_someone_who_is_not_a_member_reports_that_nothing_matched(self, assigner, member, global_role):
        response = client_for(assigner).delete(_member_url(global_role, member))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "No global role membership matches the given query."

    def test_removing_an_unknown_user_is_a_404(self, assigner, global_role):
        response = client_for(assigner).delete(reverse("global_role_member_details", args=[global_role.id, 9999]))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_removing_the_same_member_twice_only_succeeds_once(self, assigner, member, global_role):
        global_role.members.add(member)
        client = client_for(assigner)

        assert client.delete(_member_url(global_role, member)).status_code == status.HTTP_204_NO_CONTENT
        assert client.delete(_member_url(global_role, member)).status_code == status.HTTP_404_NOT_FOUND


class TestWhatMembershipActuallyDoes:
    def test_an_assigner_may_add_themselves_to_a_group(self, assigner, global_role, members_url):
        response = client_for(assigner).post(members_url, {"user_id": assigner.id}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert global_role.members.filter(pk=assigner.pk).exists()

    def test_the_group_s_permissions_reach_a_newly_added_member(self, assigner, member):
        global_role = make_global_role("user-managers", PERMISSIONS.USER.VIEW)
        url = reverse("global_role_member_list", args=[global_role.id])

        assert client_for(member).get(reverse("user_list")).status_code == status.HTTP_403_FORBIDDEN

        client_for(assigner).post(url, {"user_id": member.id}, format="json")

        response = client_for(User.objects.get(pk=member.pk)).get(reverse("user_list"))

        assert response.status_code == status.HTTP_200_OK
