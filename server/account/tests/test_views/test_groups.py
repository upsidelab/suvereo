import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.models import DatasetGroupRoleAssignment, User, UserGroup
from account.tests.helpers import (
    assign_role,
    client_for,
    grant,
    join_group,
    make_global_role,
    make_group,
    make_role,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def group():
    return make_group("contractors")


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


class TestWritingGroupsNeedsItsOwnLifecycleCode:
    @pytest.mark.parametrize(
        ("method", "uses_detail_url", "body", "code", "expected_status"),
        [
            ("post", False, {"name": "new-bucket"}, PERMISSIONS.GROUP.ADD, status.HTTP_201_CREATED),
            ("patch", True, {"name": "renamed"}, PERMISSIONS.GROUP.CHANGE, status.HTTP_200_OK),
            ("put", True, {"name": "renamed"}, PERMISSIONS.GROUP.CHANGE, status.HTTP_200_OK),
            ("delete", True, None, PERMISSIONS.GROUP.DELETE, status.HTTP_204_NO_CONTENT),
        ],
        ids=["create", "patch name", "rename", "delete"],
    )
    def test_a_holder_of_the_code_can_write(
        self, user, list_url, detail_url, group, method, uses_detail_url, body, code, expected_status
    ):
        grant(user, PERMISSIONS.GROUP.VIEW, code)
        url = detail_url if uses_detail_url else list_url

        response = getattr(client_for(user), method)(url, body, format="json")

        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        ("method", "uses_detail_url", "body"),
        [
            ("post", False, {"name": "new-bucket"}),
            ("patch", True, {"name": "renamed"}),
            ("put", True, {"name": "renamed"}),
            ("delete", True, None),
        ],
        ids=["create", "patch name", "rename", "delete"],
    )
    def test_reading_and_assigning_do_not_carry_the_write(
        self, user, list_url, detail_url, group, method, uses_detail_url, body
    ):
        grant(user, PERMISSIONS.GROUP.VIEW, PERMISSIONS.GROUP.ASSIGN)
        url = detail_url if uses_detail_url else list_url

        response = getattr(client_for(user), method)(url, body, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert UserGroup.objects.filter(pk=group.pk, name="contractors").exists()
        assert not UserGroup.objects.filter(name__in=["new-bucket", "renamed"]).exists()

    def test_an_admin_still_reaches_every_write(self, admin_api_client, list_url):
        response = admin_api_client.post(list_url, {"name": "new-bucket"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert UserGroup.objects.filter(name="new-bucket").exists()

    def test_a_duplicate_name_is_refused(self, admin_api_client, list_url, group):
        response = admin_api_client.post(list_url, {"name": "contractors"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert str(response.data["name"][0]) == "A group with this name already exists."


class TestGroupPayloads:
    def test_the_listing_carries_the_name_and_the_counts(self, api_client, user, list_url, group, data_set):
        """The counts are what makes a group's reach legible before anyone grants it anything."""
        grant(user, PERMISSIONS.GROUP.VIEW)
        group.members.add(user, baker.make(User, email="second@example.com"))
        group.global_roles.add(make_global_role("viewers"), make_global_role("auditors"))
        assign_role(group, data_set, make_role("reader", PERMISSIONS.AGENT.VIEW))
        assign_role(group, data_set, make_role("converser", PERMISSIONS.CONVERSATION.CONVERSE))

        response = api_client.get(list_url)

        assert response.data["results"] == [
            {
                "id": group.id,
                "name": "contractors",
                "member_count": 2,
                "global_role_count": 2,
                "data_set_role_count": 2,
            }
        ]

    def test_a_group_just_created_reports_no_reach(self, admin_api_client, list_url):
        response = admin_api_client.post(list_url, {"name": "new-bucket"}, format="json")

        assert response.data["member_count"] == 0
        assert response.data["global_role_count"] == 0
        assert response.data["data_set_role_count"] == 0

    def test_the_detail_carries_the_global_roles_the_group_holds(self, api_client, user, detail_url, group):
        grant(user, PERMISSIONS.GROUP.VIEW)
        global_role = make_global_role("viewers", PERMISSIONS.DATA_SET.VIEW)
        group.global_roles.add(global_role)

        response = api_client.get(detail_url)

        assert response.data["global_roles"] == [{"id": global_role.id, "name": "viewers"}]

    def test_the_global_roles_a_group_holds_are_read_only_on_this_endpoint(self, admin_api_client, detail_url, group):
        """Granting one is `/api/groups/<id>/global_roles`, gated on `global_role.assign`, so this
        endpoint only reads them - naming the field in a body here changes nothing. DRF drops a
        read-only field silently, so the `200` is a rename that happened to carry extra keys."""
        global_role = make_global_role("viewers", PERMISSIONS.DATA_SET.VIEW)

        response = admin_api_client.patch(detail_url, {"global_roles": [global_role.id]}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert not group.global_roles.exists()

    def test_the_listing_does_not_query_once_per_group(self, api_client, user, list_url, data_set):
        """The counts are annotated, so the listing costs the same whether it returns one group or
        forty. Asserted as "does not grow with the rows" rather than as a fixed number, which an
        unrelated query elsewhere in the request would break without anything being wrong."""
        grant(user, PERMISSIONS.GROUP.VIEW)
        self._populate(user, data_set, indices=range(1))
        for_one = self._query_count(api_client, list_url)

        self._populate(user, data_set, indices=range(1, 4))
        for_four = self._query_count(api_client, list_url)

        assert for_four == for_one

    @staticmethod
    def _populate(user, data_set, indices):
        for index in indices:
            group = make_group(f"bucket-{index}")
            join_group(user, group)
            group.global_roles.add(make_global_role(f"role-{index}"))
            assign_role(group, data_set, make_role(f"reader-{index}", PERMISSIONS.AGENT.VIEW))

    @staticmethod
    def _query_count(client, url) -> int:
        """Warms the request user's permission cache first: joining a group drops it, so an
        un-warmed measurement charges the listing for a permission lookup it did not make."""
        client.get(url)
        with CaptureQueriesContext(connection) as captured:
            client.get(url)
        return len(captured)


class TestGroupDeletion:
    def test_deleting_a_group_takes_its_memberships_with_it(self, admin_api_client, detail_url, group, user):
        join_group(user, group)

        response = admin_api_client.delete(detail_url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not UserGroup.objects.filter(pk=group.pk).exists()
        assert not user.user_groups.exists()

    def test_deleting_a_group_gives_up_the_dataset_roles_it_held(self, admin_api_client, detail_url, group, data_set):
        assign_role(group, data_set, make_role("reader", PERMISSIONS.AGENT.VIEW))

        response = admin_api_client.delete(detail_url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not DatasetGroupRoleAssignment.objects.filter(group_id=group.pk).exists()

    def test_deleting_a_group_leaves_the_global_roles_it_held_alone(self, admin_api_client, detail_url, group):
        global_role = make_global_role("viewers", PERMISSIONS.DATA_SET.VIEW)
        group.global_roles.add(global_role)

        admin_api_client.delete(detail_url)

        assert type(global_role).objects.filter(pk=global_role.pk).exists()
