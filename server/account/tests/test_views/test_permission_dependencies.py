import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status

from account.authorization import PERMISSIONS
from account.models import DatasetRole
from account.tests.helpers import permission
from account.tests.public_permission_codes_contract import (
    AGENT_ADD,
    AGENT_CHANGE,
    AGENT_VIEW,
    AGENTIC_EXECUTION_CREATE,
    CONVERSATION_CONVERSE,
    DATASET_ROLE_ASSIGN,
    DATASET_VIEW,
    GROUP_ASSIGN,
    GROUP_VIEW,
    INTEGRATION_SYNC,
    INTEGRATION_VIEW,
    USER_ADD,
    USER_VIEW,
)

pytestmark = pytest.mark.django_db

NOT_GRANTABLE_ON_A_ROLE = (
    "A dataset role can only carry dataset-scoped permissions, so these cannot be granted on one: {codes}."
)


def requires(required: str, by: list[str]) -> str:
    return f"{required} is required by {', '.join(by)}."


def _errors(response) -> list[str]:
    return [str(error) for error in response.data["permissions"]]


class TestDependenciesOnAGroup:
    """Global scope - every requirement in the map applies."""

    @pytest.fixture
    def url(self):
        return reverse("group_list")

    @pytest.mark.parametrize(
        ("codes", "expected_errors"),
        [
            pytest.param(
                [AGENT_CHANGE],
                [requires(AGENT_VIEW, by=[AGENT_CHANGE]), requires(DATASET_VIEW, by=[AGENT_CHANGE])],
                id="every unmet requirement is reported in one response",
            ),
            pytest.param(
                [AGENT_CHANGE, AGENT_VIEW],
                [requires(DATASET_VIEW, by=[AGENT_CHANGE, AGENT_VIEW])],
                id="the message names every permission that caused the requirement",
            ),
            pytest.param([AGENT_CHANGE, AGENT_VIEW, DATASET_VIEW], None, id="satisfied"),
            pytest.param(
                [INTEGRATION_SYNC],
                [
                    requires(DATASET_VIEW, by=[INTEGRATION_SYNC]),
                    requires(INTEGRATION_VIEW, by=[INTEGRATION_SYNC]),
                ],
                id="sync is not carved out of the integration requirements",
            ),
            pytest.param([INTEGRATION_SYNC, INTEGRATION_VIEW, DATASET_VIEW], None, id="sync satisfied"),
            pytest.param(
                [GROUP_ASSIGN],
                [requires(GROUP_VIEW, by=[GROUP_ASSIGN])],
                id="assigning members requires seeing the group",
            ),
            pytest.param(
                [GROUP_ASSIGN, GROUP_VIEW],
                None,
                id="group is not dataset-scoped, so no dataset.view is demanded",
            ),
            pytest.param(
                [USER_ADD],
                [requires(USER_VIEW, by=[USER_ADD])],
                id="user is not dataset-scoped either",
            ),
            pytest.param(
                [CONVERSATION_CONVERSE],
                [requires(DATASET_VIEW, by=[CONVERSATION_CONVERSE])],
                id="converse requires nothing itself but is dataset-scoped",
            ),
            pytest.param([CONVERSATION_CONVERSE, DATASET_VIEW], None, id="converse satisfied"),
            pytest.param(
                [AGENTIC_EXECUTION_CREATE, DATASET_VIEW],
                None,
                id="create is a deliberate absence and does not demand view_all",
            ),
            pytest.param(
                [DATASET_ROLE_ASSIGN],
                [requires(DATASET_VIEW, by=[DATASET_ROLE_ASSIGN])],
                id="dataset_role.assign does not require dataset_role.view, unlike group.assign",
            ),
            pytest.param([DATASET_ROLE_ASSIGN, DATASET_VIEW], None, id="dataset_role.assign satisfied"),
            pytest.param([DATASET_VIEW], None, id="dataset.view requires nothing"),
            pytest.param([], None, id="an empty set is valid"),
            # Not from the contract module on purpose: these are strings the vocabulary must refuse.
            pytest.param(
                ["group.add"],
                ["Unknown permission: group.add."],
                id="an undeclared Django permission is not a code",
            ),
            pytest.param(
                ["agent.frobnicate"],
                ["Unknown permission: agent.frobnicate."],
                id="a typo is indistinguishable from an undeclared code, by design",
            ),
        ],
    )
    def test_permission_set_is_validated_against_the_global_scope(self, admin_api_client, url, codes, expected_errors):
        response = admin_api_client.post(url, {"name": "team", "permissions": codes}, format="json")

        if expected_errors is None:
            assert response.status_code == status.HTTP_201_CREATED
            assert set(response.data["permissions"]) == set(codes)
        else:
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert _errors(response) == expected_errors
            assert not Group.objects.filter(name="team").exists()

    def test_permissions_may_be_omitted_entirely(self, admin_api_client, url):
        response = admin_api_client.post(url, {"name": "team"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["permissions"] == []


class TestDependenciesOnADatasetRole:
    """Dataset scope - requirements the scope cannot grant are dropped, not made unsatisfiable."""

    @pytest.fixture
    def url(self):
        return reverse("dataset_role_list")

    @pytest.mark.parametrize(
        ("codes", "expected_errors"),
        [
            pytest.param(
                [AGENT_ADD],
                [requires(AGENT_VIEW, by=[AGENT_ADD])],
                id="no dataset.view is demanded, unlike on a group",
            ),
            pytest.param([AGENT_ADD, AGENT_VIEW], None, id="satisfied"),
            pytest.param(
                [INTEGRATION_SYNC],
                [requires(INTEGRATION_VIEW, by=[INTEGRATION_SYNC])],
                id="within-entity requirements still apply",
            ),
            pytest.param([INTEGRATION_SYNC, INTEGRATION_VIEW], None, id="sync satisfied"),
            pytest.param([CONVERSATION_CONVERSE], None, id="converse has no requirements in this scope"),
            pytest.param(
                [DATASET_ROLE_ASSIGN],
                None,
                id="per-dataset delegation would be unconstructable if this required anything",
            ),
            pytest.param(
                [USER_ADD, USER_VIEW],
                [NOT_GRANTABLE_ON_A_ROLE.format(codes=f"{USER_ADD}, {USER_VIEW}")],
                id="a global-only entity is refused before dependencies are considered",
            ),
            pytest.param(
                [DATASET_VIEW],
                [NOT_GRANTABLE_ON_A_ROLE.format(codes=DATASET_VIEW)],
                id="dataset itself is global-only",
            ),
        ],
    )
    def test_permission_set_is_validated_against_the_dataset_scope(self, admin_api_client, url, codes, expected_errors):
        response = admin_api_client.post(url, {"name": "editor", "permissions": codes}, format="json")

        if expected_errors is None:
            assert response.status_code == status.HTTP_201_CREATED
            assert set(response.data["permissions"]) == set(codes)
        else:
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert _errors(response) == expected_errors
            assert not DatasetRole.objects.filter(name="editor").exists()


class TestDependenciesAreEnforcedOnUpdate:
    @pytest.fixture
    def group(self, admin_api_client):
        response = admin_api_client.post(
            reverse("group_list"),
            {"name": "team", "permissions": [AGENT_CHANGE, AGENT_VIEW, DATASET_VIEW]},
            format="json",
        )
        return Group.objects.get(pk=response.data["id"])

    @pytest.fixture
    def url(self, group):
        return reverse("group_details", args=[group.id])

    def test_patching_into_a_violating_set_is_refused_and_leaves_the_stored_set_alone(
        self, admin_api_client, url, group
    ):
        before = set(group.permissions.values_list("codename", flat=True))

        response = admin_api_client.patch(url, {"permissions": [AGENT_CHANGE]}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert set(group.permissions.values_list("codename", flat=True)) == before

    def test_patching_can_satisfy_a_requirement_by_adding_to_the_set(self, admin_api_client):
        group = Group.objects.create(name="viewers")
        group.permissions.add(permission(PERMISSIONS.DATASET.VIEW))

        response = admin_api_client.patch(
            reverse("group_details", args=[group.id]),
            {"permissions": [AGENT_CHANGE, AGENT_VIEW, DATASET_VIEW]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert set(response.data["permissions"]) == {AGENT_CHANGE, AGENT_VIEW, DATASET_VIEW}

    def test_a_permission_set_round_trips_and_is_replaced_wholesale(self, admin_api_client, url):
        response = admin_api_client.get(url)

        assert set(response.data["permissions"]) == {AGENT_CHANGE, AGENT_VIEW, DATASET_VIEW}

        replaced = admin_api_client.patch(url, {"permissions": [DATASET_VIEW]}, format="json")

        assert replaced.status_code == status.HTTP_200_OK
        assert replaced.data["permissions"] == [DATASET_VIEW]


class TestNothingIsSilentlyAdded:
    def test_an_accepted_set_is_stored_exactly_as_sent(self, admin_api_client):
        """A requirement quietly appended would hide what was actually decided from whoever reads
        the group later - `dataset.view` grants sight of every data set in the system."""
        sent = [AGENT_CHANGE, AGENT_VIEW, DATASET_VIEW]

        response = admin_api_client.post(reverse("group_list"), {"name": "team", "permissions": sent}, format="json")
        group = Group.objects.get(pk=response.data["id"])

        assert set(response.data["permissions"]) == set(sent)
        assert group.permissions.count() == len(sent)

    def test_a_declared_code_whose_row_is_missing_is_reported_rather_than_skipped(self, admin_api_client):
        """The failure mode if a model's `Meta.permissions` is ever edited without a migration.
        Accepting the save would store a grant with a silently missing permission in it."""
        permission(PERMISSIONS.DATASET.VIEW).delete()

        response = admin_api_client.post(
            reverse("group_list"), {"name": "team", "permissions": [DATASET_VIEW]}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert _errors(response) == [f"Permission {DATASET_VIEW} is declared but missing from the database."]
