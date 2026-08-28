import pytest
from django.urls import reverse
from rest_framework import status

from account.authorization import PERMISSIONS
from account.models import DatasetRole, GlobalRole
from account.tests.helpers import permission
from account.tests.public_permission_codes_contract import (
    AGENT_ADD,
    AGENT_CHANGE,
    AGENT_VIEW,
    AGENTIC_EXECUTION_CREATE,
    CONVERSATION_CONVERSE,
    DATASET_ROLE_ADD,
    DATASET_ROLE_ASSIGN,
    DATASET_ROLE_CHANGE,
    DATASET_ROLE_DELETE,
    DATASET_ROLE_VIEW,
    DATASET_VIEW,
    GLOBAL_ROLE_ADD,
    GLOBAL_ROLE_ASSIGN,
    GLOBAL_ROLE_DELETE,
    GLOBAL_ROLE_VIEW,
    GROUP_ADD,
    GROUP_ASSIGN,
    GROUP_CHANGE,
    GROUP_DELETE,
    GROUP_VIEW,
    INTEGRATION_SYNC,
    INTEGRATION_VIEW,
    SERVICE_ACCOUNT_VIEW,
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


class TestDependenciesOnAGlobalRole:
    """Global scope - every requirement in the map applies."""

    @pytest.fixture
    def url(self):
        return reverse("global_role_list")

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
                [GLOBAL_ROLE_ASSIGN],
                [
                    requires(GLOBAL_ROLE_VIEW, by=[GLOBAL_ROLE_ASSIGN]),
                    requires(GROUP_VIEW, by=[GLOBAL_ROLE_ASSIGN]),
                    requires(SERVICE_ACCOUNT_VIEW, by=[GLOBAL_ROLE_ASSIGN]),
                    requires(USER_VIEW, by=[GLOBAL_ROLE_ASSIGN]),
                ],
                id="assigning members requires seeing the global_role and every kind of subject",
            ),
            pytest.param(
                [GLOBAL_ROLE_ASSIGN, GLOBAL_ROLE_VIEW, USER_VIEW, SERVICE_ACCOUNT_VIEW, GROUP_VIEW],
                None,
                id="global_role is not dataset-scoped, so no dataset.view is demanded",
            ),
            pytest.param(
                [USER_ADD],
                [requires(USER_VIEW, by=[USER_ADD])],
                id="user is not dataset-scoped either",
            ),
            pytest.param(
                [CONVERSATION_CONVERSE],
                [
                    requires(AGENT_VIEW, by=[CONVERSATION_CONVERSE]),
                    requires(DATASET_VIEW, by=[CONVERSATION_CONVERSE]),
                ],
                id="conversing requires seeing the agents to converse with",
            ),
            pytest.param([CONVERSATION_CONVERSE, AGENT_VIEW, DATASET_VIEW], None, id="converse satisfied"),
            pytest.param(
                [AGENTIC_EXECUTION_CREATE, AGENT_VIEW, DATASET_VIEW],
                None,
                id="create demands the agents it runs, but still not view_all",
            ),
            pytest.param(
                [AGENTIC_EXECUTION_CREATE, DATASET_VIEW],
                [requires(AGENT_VIEW, by=[AGENTIC_EXECUTION_CREATE])],
                id="running an agent requires seeing it",
            ),
            pytest.param(
                [DATASET_ROLE_ASSIGN],
                [
                    requires(DATASET_VIEW, by=[DATASET_ROLE_ASSIGN]),
                    requires(DATASET_ROLE_VIEW, by=[DATASET_ROLE_ASSIGN]),
                    requires(GROUP_VIEW, by=[DATASET_ROLE_ASSIGN]),
                    requires(SERVICE_ACCOUNT_VIEW, by=[DATASET_ROLE_ASSIGN]),
                    requires(USER_VIEW, by=[DATASET_ROLE_ASSIGN]),
                ],
                id="dataset_role.assign requires dataset_role.view, exactly like global_role.assign",
            ),
            pytest.param(
                [DATASET_ROLE_ASSIGN, DATASET_VIEW, DATASET_ROLE_VIEW, USER_VIEW, SERVICE_ACCOUNT_VIEW, GROUP_VIEW],
                None,
                id="dataset_role.assign satisfied",
            ),
            pytest.param([DATASET_VIEW], None, id="dataset.view requires nothing"),
            pytest.param([], None, id="an empty set is valid"),
            pytest.param(
                [GLOBAL_ROLE_ADD, GLOBAL_ROLE_DELETE],
                [requires(GLOBAL_ROLE_VIEW, by=[GLOBAL_ROLE_ADD, GLOBAL_ROLE_DELETE])],
                id="editing the global role catalogue requires seeing it",
            ),
            pytest.param(
                [GLOBAL_ROLE_ADD, GLOBAL_ROLE_DELETE, GLOBAL_ROLE_VIEW],
                None,
                id="the global role lifecycle codes require nothing but their own view",
            ),
            pytest.param(
                [DATASET_ROLE_ADD, DATASET_ROLE_CHANGE, DATASET_ROLE_DELETE],
                [requires(DATASET_ROLE_VIEW, by=[DATASET_ROLE_ADD, DATASET_ROLE_CHANGE, DATASET_ROLE_DELETE])],
                id="the dataset role lifecycle codes require their own view, and no dataset.view",
            ),
            pytest.param(
                [DATASET_ROLE_ADD, DATASET_ROLE_CHANGE, DATASET_ROLE_DELETE, DATASET_ROLE_VIEW],
                None,
                id="dataset role lifecycle satisfied",
            ),
            pytest.param(
                [GROUP_ADD, GROUP_CHANGE, GROUP_DELETE],
                [requires(GROUP_VIEW, by=[GROUP_ADD, GROUP_CHANGE, GROUP_DELETE])],
                id="the group lifecycle codes require their own view, and nothing else",
            ),
            pytest.param(
                [GROUP_ADD, GROUP_CHANGE, GROUP_DELETE, GROUP_VIEW],
                None,
                id="group lifecycle satisfied",
            ),
            # Not from the contract module on purpose: these are strings the vocabulary must refuse.
            pytest.param(
                ["user.delete"],
                ["Unknown permission: user.delete."],
                id="a Django permission the vocabulary does not declare is not a code",
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
            assert not GlobalRole.objects.filter(name="team").exists()

    def test_permissions_may_be_omitted_entirely(self, admin_api_client, url):
        response = admin_api_client.post(url, {"name": "team"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["permissions"] == []


class TestGroupAssignCannotStandAlone:
    @pytest.fixture
    def url(self):
        return reverse("global_role_list")

    def _post(self, client, url, codes):
        return client.post(url, {"name": "team", "permissions": codes}, format="json")

    def test_without_global_role_assign_it_is_rejected_naming_that_requirement(self, admin_api_client, url):
        response = self._post(
            admin_api_client,
            url,
            [GROUP_ASSIGN, GROUP_VIEW, DATASET_ROLE_ASSIGN, USER_VIEW, SERVICE_ACCOUNT_VIEW],
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert requires(GLOBAL_ROLE_ASSIGN, by=[GROUP_ASSIGN]) in _errors(response)

    def test_without_dataset_role_assign_it_is_rejected_naming_that_requirement(self, admin_api_client, url):
        response = self._post(
            admin_api_client,
            url,
            [GROUP_ASSIGN, GROUP_VIEW, GLOBAL_ROLE_ASSIGN, USER_VIEW, SERVICE_ACCOUNT_VIEW],
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert requires(DATASET_ROLE_ASSIGN, by=[GROUP_ASSIGN]) in _errors(response)

    def test_without_either_one_response_names_both(self, admin_api_client, url):
        response = self._post(admin_api_client, url, [GROUP_ASSIGN, GROUP_VIEW, USER_VIEW, SERVICE_ACCOUNT_VIEW])

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert requires(GLOBAL_ROLE_ASSIGN, by=[GROUP_ASSIGN]) in _errors(response)
        assert requires(DATASET_ROLE_ASSIGN, by=[GROUP_ASSIGN]) in _errors(response)

    def test_the_whole_chain_is_named_at_once_against_the_permission_that_was_ticked(self, admin_api_client, url):
        """`group.assign` requires both assign codes, which require their own views and - through
        `dataset_role.assign` - `dataset.view`. Every one of them is reported against `group.assign`
        itself, because that is the box the admin ticked. A one-level walk names three of these and
        rejects the save four more times as each is answered."""
        response = self._post(admin_api_client, url, [GROUP_ASSIGN])

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert _errors(response) == [
            requires(DATASET_VIEW, by=[GROUP_ASSIGN]),
            requires(DATASET_ROLE_ASSIGN, by=[GROUP_ASSIGN]),
            requires(DATASET_ROLE_VIEW, by=[GROUP_ASSIGN]),
            requires(GLOBAL_ROLE_ASSIGN, by=[GROUP_ASSIGN]),
            requires(GLOBAL_ROLE_VIEW, by=[GROUP_ASSIGN]),
            requires(GROUP_VIEW, by=[GROUP_ASSIGN]),
            requires(SERVICE_ACCOUNT_VIEW, by=[GROUP_ASSIGN]),
            requires(USER_VIEW, by=[GROUP_ASSIGN]),
        ]

    def test_the_chain_satisfied_in_one_save(self, admin_api_client, url):
        response = self._post(
            admin_api_client,
            url,
            [
                GROUP_ASSIGN,
                GROUP_VIEW,
                GLOBAL_ROLE_ASSIGN,
                GLOBAL_ROLE_VIEW,
                DATASET_ROLE_ASSIGN,
                DATASET_ROLE_VIEW,
                DATASET_VIEW,
                USER_VIEW,
                SERVICE_ACCOUNT_VIEW,
            ],
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_attaching_a_role_to_a_group_is_not_what_this_gates(self, admin_api_client, url):
        """The dependency runs one way only. A `dataset_role.assign` holder could grant that role
        to each member directly, so routing it through the group is the same effect by a shorter
        path - and needs nothing `group.assign` does not."""
        response = self._post(
            admin_api_client,
            url,
            [DATASET_ROLE_ASSIGN, DATASET_VIEW, DATASET_ROLE_VIEW, GROUP_VIEW, USER_VIEW, SERVICE_ACCOUNT_VIEW],
        )

        assert response.status_code == status.HTTP_201_CREATED


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
                id="no dataset.view is demanded, unlike on a global_role",
            ),
            pytest.param([AGENT_ADD, AGENT_VIEW], None, id="satisfied"),
            pytest.param(
                [INTEGRATION_SYNC],
                [requires(INTEGRATION_VIEW, by=[INTEGRATION_SYNC])],
                id="within-entity requirements still apply",
            ),
            pytest.param([INTEGRATION_SYNC, INTEGRATION_VIEW], None, id="sync satisfied"),
            pytest.param(
                [CONVERSATION_CONVERSE],
                [requires(AGENT_VIEW, by=[CONVERSATION_CONVERSE])],
                id="converse requires agent.view here too, only dataset.view is dropped",
            ),
            pytest.param([CONVERSATION_CONVERSE, AGENT_VIEW], None, id="converse satisfied"),
            pytest.param(
                [AGENTIC_EXECUTION_CREATE, AGENT_VIEW],
                None,
                id="creating an execution requires agent.view here too",
            ),
            pytest.param(
                [DATASET_ROLE_ASSIGN],
                [NOT_GRANTABLE_ON_A_ROLE.format(codes=DATASET_ROLE_ASSIGN)],
                id="assignment is global-only, so a role cannot carry it",
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
    def global_role(self, admin_api_client):
        response = admin_api_client.post(
            reverse("global_role_list"),
            {"name": "team", "permissions": [AGENT_CHANGE, AGENT_VIEW, DATASET_VIEW]},
            format="json",
        )
        return GlobalRole.objects.get(pk=response.data["id"])

    @pytest.fixture
    def url(self, global_role):
        return reverse("global_role_details", args=[global_role.id])

    def test_patching_into_a_violating_set_is_refused_and_leaves_the_stored_set_alone(
        self, admin_api_client, url, global_role
    ):
        before = set(global_role.permissions.values_list("codename", flat=True))

        response = admin_api_client.patch(url, {"permissions": [AGENT_CHANGE]}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert set(global_role.permissions.values_list("codename", flat=True)) == before

    def test_patching_can_satisfy_a_requirement_by_adding_to_the_set(self, admin_api_client):
        global_role = GlobalRole.objects.create(name="viewers")
        global_role.permissions.add(permission(PERMISSIONS.DATA_SET.VIEW))

        response = admin_api_client.patch(
            reverse("global_role_details", args=[global_role.id]),
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
        the global_role later - `dataset.view` grants sight of every data set in the system."""
        sent = [AGENT_CHANGE, AGENT_VIEW, DATASET_VIEW]

        response = admin_api_client.post(
            reverse("global_role_list"), {"name": "team", "permissions": sent}, format="json"
        )
        global_role = GlobalRole.objects.get(pk=response.data["id"])

        assert set(response.data["permissions"]) == set(sent)
        assert global_role.permissions.count() == len(sent)

    def test_a_declared_code_whose_row_is_missing_is_reported_rather_than_skipped(self, admin_api_client):
        """The failure mode if a model's `Meta.permissions` is ever edited without a migration.
        Accepting the save would store a grant with a silently missing permission in it."""
        permission(PERMISSIONS.DATA_SET.VIEW).delete()

        response = admin_api_client.post(
            reverse("global_role_list"), {"name": "team", "permissions": [DATASET_VIEW]}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert _errors(response) == [f"Permission {DATASET_VIEW} is declared but missing from the database."]
