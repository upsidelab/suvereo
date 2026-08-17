import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS, has_dataset_perm
from account.models import DatasetGroupRoleAssignment, DatasetUserRoleAssignment, User
from account.tests.helpers import assign_role, client_for, grant, join_group, make_group, make_role
from catalog.models import DataSet

pytestmark = pytest.mark.django_db

DATA_SET_NOT_FOUND = {"detail": "No DataSet matches the given query."}


@pytest.fixture
def other_data_set():
    return baker.make(DataSet)


@pytest.fixture
def role():
    return make_role("reader", PERMISSIONS.AGENT.VIEW)


@pytest.fixture
def assigner(user, data_set):
    """Holds `dataset_role.assign` on `data_set` only, which is how a per-dataset delegate looks."""
    assign_role(user, data_set, make_role("access-manager", PERMISSIONS.DATASET_ROLE.ASSIGN))
    return user


@pytest.fixture
def global_assigner():
    return grant(baker.make(User, email="global@example.com"), PERMISSIONS.DATASET_ROLE.ASSIGN)


@pytest.fixture
def subject():
    return baker.make(User, email="subject@example.com")


def access_url(data_set) -> str:
    return reverse("dataset_access_list", args=[data_set.id])


def grant_url(data_set, role, kind="users") -> str:
    return reverse(f"dataset_role_{kind[:-1]}_list", args=[data_set.id, role.id])


def revoke_url(data_set, role, subject, kind="users") -> str:
    return reverse(f"dataset_role_{kind[:-1]}_details", args=[data_set.id, role.id, subject.id])


class TestWhoCanSeeADataSetsAccessList:
    def test_returns_401_when_unauthenticated(self, data_set):
        assert APIClient().get(access_url(data_set)).status_code == status.HTTP_401_UNAUTHORIZED

    def test_a_global_assign_holder_is_allowed(self, global_assigner, data_set):
        response = client_for(global_assigner).get(access_url(data_set))

        assert response.status_code == status.HTTP_200_OK

    def test_a_per_dataset_assign_holder_is_allowed_on_their_own_data_set(self, assigner, data_set):
        response = client_for(assigner).get(access_url(data_set))

        assert response.status_code == status.HTTP_200_OK

    def test_a_member_without_the_assign_grant_is_forbidden(self, user, data_set):
        """The data set is already visible to them, so there is nothing left to hide - what they
        are missing is the capability, and `403` says exactly that."""
        assign_role(user, data_set, make_role("converser", PERMISSIONS.CONVERSATION.CONVERSE))

        response = client_for(user).get(access_url(data_set))

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_an_outsider_is_told_the_data_set_does_not_exist(self, api_client, data_set):
        response = api_client.get(access_url(data_set))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == DATA_SET_NOT_FOUND

    def test_the_outsiders_404_is_identical_to_a_missing_data_sets(self, api_client, data_set):
        hidden = api_client.get(access_url(data_set))
        missing = api_client.get(reverse("dataset_access_list", args=[9999]))

        assert hidden.status_code == missing.status_code
        assert hidden.data == missing.data


class TestTheAccessListPayload:
    def test_reports_one_row_per_assignment_keyed_by_subject_kind(self, global_assigner, data_set, role, subject):
        group = make_group("support")
        user_assignment = assign_role(subject, data_set, role)
        group_assignment = assign_role(group, data_set, role)

        response = client_for(global_assigner).get(access_url(data_set))

        assert [row["id"] for row in response.data["users"]] == [user_assignment.id]
        assert response.data["users"][0]["user"]["id"] == subject.id
        assert response.data["users"][0]["role"]["id"] == role.id
        assert [row["id"] for row in response.data["groups"]] == [group_assignment.id]
        assert response.data["groups"][0]["group"]["id"] == group.id


class TestGrantingARole:
    @pytest.mark.parametrize("kind", ["users", "groups"])
    def test_a_role_granted_to_a_user_or_a_group_reaches_the_subject(
        self, global_assigner, data_set, role, subject, kind
    ):
        """Granted to a group, the role has to reach the group's members - that indirection is the
        only reason granting to a group is worth having."""
        if kind == "users":
            body = {"user_id": subject.id}
        else:
            group = make_group("support")
            join_group(subject, group)
            body = {"group_id": group.id}

        response = client_for(global_assigner).post(grant_url(data_set, role, kind), body, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert has_dataset_perm(subject, PERMISSIONS.AGENT.VIEW, data_set)

    def test_several_roles_compose_into_the_union_of_their_permissions(self, global_assigner, data_set, subject):
        client = client_for(global_assigner)
        roles = [
            make_role("agent-reader", PERMISSIONS.AGENT.VIEW),
            make_role("integration-reader", PERMISSIONS.INTEGRATION.VIEW),
            make_role("converser", PERMISSIONS.CONVERSATION.CONVERSE),
        ]

        for role in roles:
            client.post(grant_url(data_set, role), {"user_id": subject.id}, format="json")

        assert has_dataset_perm(subject, PERMISSIONS.AGENT.VIEW, data_set)
        assert has_dataset_perm(subject, PERMISSIONS.INTEGRATION.VIEW, data_set)
        assert has_dataset_perm(subject, PERMISSIONS.CONVERSATION.CONVERSE, data_set)

    def test_granting_the_same_role_twice_reports_no_change(self, global_assigner, data_set, role, subject):
        client = client_for(global_assigner)
        url = grant_url(data_set, role)

        first = client.post(url, {"user_id": subject.id}, format="json")
        second = client.post(url, {"user_id": subject.id}, format="json")

        assert first.status_code == status.HTTP_201_CREATED
        assert second.status_code == status.HTTP_200_OK
        assert DatasetUserRoleAssignment.objects.filter(user=subject, dataset=data_set).count() == 1

    def test_granting_a_different_role_adds_a_second_row(self, global_assigner, data_set, role, subject):
        client = client_for(global_assigner)
        other_role = make_role("converser", PERMISSIONS.CONVERSATION.CONVERSE)

        client.post(grant_url(data_set, role), {"user_id": subject.id}, format="json")
        response = client.post(grant_url(data_set, other_role), {"user_id": subject.id}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert DatasetUserRoleAssignment.objects.filter(user=subject, dataset=data_set).count() == 2

    def test_a_service_account_can_be_granted_a_role(self, global_assigner, data_set, role):
        service_account = baker.make(User, email="bot@example.com", is_service_account=True)

        response = client_for(global_assigner).post(
            grant_url(data_set, role), {"user_id": service_account.id}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert has_dataset_perm(service_account, PERMISSIONS.AGENT.VIEW, data_set)

    def test_an_unknown_role_in_the_path_is_a_404(self, global_assigner, data_set, subject):
        response = client_for(global_assigner).post(
            reverse("dataset_role_user_list", args=[data_set.id, 9999]), {"user_id": subject.id}, format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_an_outsider_is_refused_before_the_role_is_looked_up(self, api_client, data_set, role, subject):
        """The data set gate runs first, so the response says nothing about whether the role in the
        path exists - otherwise the endpoint would enumerate roles for anyone."""
        response = api_client.post(grant_url(data_set, role), {"user_id": subject.id}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == DATA_SET_NOT_FOUND
        assert not DatasetUserRoleAssignment.objects.exists()


class TestRevokingARole:
    def test_revoking_one_role_leaves_the_others_in_force(self, global_assigner, data_set, subject):
        reader = make_role("agent-reader", PERMISSIONS.AGENT.VIEW)
        converser = make_role("converser", PERMISSIONS.CONVERSATION.CONVERSE)
        assign_role(subject, data_set, reader)
        assign_role(subject, data_set, converser)

        response = client_for(global_assigner).delete(revoke_url(data_set, reader, subject))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not has_dataset_perm(subject, PERMISSIONS.AGENT.VIEW, data_set)
        assert has_dataset_perm(subject, PERMISSIONS.CONVERSATION.CONVERSE, data_set)

    @pytest.mark.parametrize("kind", ["users", "groups"])
    def test_revoking_a_role_the_subject_does_not_hold_reports_that_nothing_matched(
        self, global_assigner, data_set, role, subject, kind
    ):
        target = subject if kind == "users" else make_group("support")
        model = "DatasetUserRoleAssignment" if kind == "users" else "DatasetGroupRoleAssignment"

        response = client_for(global_assigner).delete(revoke_url(data_set, role, target, kind))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == {"detail": f"No {model} matches the given query."}

    @pytest.mark.parametrize("wrong", ["subject", "role"], ids=["typo'd subject id", "typo'd role id"])
    def test_a_revoke_with_a_mistyped_id_does_not_report_success(self, global_assigner, data_set, role, subject, wrong):
        """The case this rule exists for: a script revoking access with the wrong id used to get a
        `204` and move on, leaving the access in place."""
        assign_role(subject, data_set, role)
        args = [data_set.id, role.id, 9999] if wrong == "subject" else [data_set.id, 9999, subject.id]

        response = client_for(global_assigner).delete(reverse("dataset_role_user_details", args=args))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert DatasetUserRoleAssignment.objects.filter(user=subject, dataset=data_set, role=role).exists()

    @pytest.mark.parametrize("kind", ["users", "groups"])
    def test_revoking_twice_only_succeeds_once(self, global_assigner, data_set, role, subject, kind):
        target = subject if kind == "users" else make_group("support")
        assign_role(target, data_set, role)
        client = client_for(global_assigner)
        url = revoke_url(data_set, role, target, kind)

        assert client.delete(url).status_code == status.HTTP_204_NO_CONTENT
        assert client.delete(url).status_code == status.HTTP_404_NOT_FOUND

    def test_revoking_a_group_role_removes_it_for_the_groups_members(self, global_assigner, data_set, role, subject):
        group = make_group("support")
        join_group(subject, group)
        assign_role(group, data_set, role)

        response = client_for(global_assigner).delete(revoke_url(data_set, role, group, "groups"))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not DatasetGroupRoleAssignment.objects.exists()
        assert not has_dataset_perm(subject, PERMISSIONS.AGENT.VIEW, data_set)


class TestHowFarAGrantReaches:
    def test_a_global_assign_grant_reaches_a_data_set_the_holder_holds_no_role_on(
        self, global_assigner, other_data_set, role, subject
    ):
        response = client_for(global_assigner).post(
            grant_url(other_data_set, role), {"user_id": subject.id}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_a_per_dataset_assign_grant_does_not_reach_another_data_set(
        self, assigner, data_set, other_data_set, role, subject
    ):
        client = client_for(assigner)

        assert client.get(access_url(data_set)).status_code == status.HTTP_200_OK

        response = client.post(grant_url(other_data_set, role), {"user_id": subject.id}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == DATA_SET_NOT_FOUND

    def test_an_assign_grant_resolves_through_group_membership(self, user, data_set):
        group = make_group("access-managers")
        join_group(user, group)
        assign_role(group, data_set, make_role("access-manager", PERMISSIONS.DATASET_ROLE.ASSIGN))

        response = client_for(user).get(access_url(data_set))

        assert response.status_code == status.HTTP_200_OK

    def test_a_role_granted_on_one_data_set_confers_nothing_on_another(self, subject, data_set, other_data_set, role):
        assign_role(subject, data_set, role)

        assert has_dataset_perm(subject, PERMISSIONS.AGENT.VIEW, data_set)
        assert not has_dataset_perm(subject, PERMISSIONS.AGENT.VIEW, other_data_set)

    def test_a_global_dual_scope_grant_reaches_every_data_set(self, subject, other_data_set):
        join_group(subject, make_group("agent-readers", PERMISSIONS.AGENT.VIEW, PERMISSIONS.DATASET.VIEW))

        response = client_for(subject).get(f"{reverse('agents')}?dataset={other_data_set.id}")

        assert response.status_code == status.HTTP_200_OK
