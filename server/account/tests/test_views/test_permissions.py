import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.tests.helpers import grant, permission
from account.tests.public_permission_codes_contract import (
    AGENT_ADD,
    AGENT_VIEW,
    DATASET_ADD,
    DATASET_ROLE_ADD,
    DATASET_ROLE_VIEW,
    DATASET_SCOPED_CONTRACT,
    DATASET_VIEW,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def url():
    return reverse("permission_list")


def _codes(response) -> set[str]:
    return {option["code"] for entity in response.data for option in entity["permissions"]}


def _requirements(response) -> dict[str, list[str]]:
    return {option["code"]: option["requires"] for entity in response.data for option in entity["permissions"]}


def _unmet_requirements(selected: list[str], requirements: dict[str, list[str]]) -> list[dict]:
    """What the role editor reports from `requires`, written the way the editor writes it."""
    granted = set(selected)
    required_by: dict[str, list[str]] = {}
    for code in selected:
        for required in requirements[code]:
            if required not in granted:
                required_by.setdefault(required, []).append(code)

    return sorted(
        ({"code": code, "required_by": sorted(dependents)} for code, dependents in required_by.items()),
        key=lambda entry: entry["code"],
    )


class TestPermissionListing:
    def test_omitting_the_scope_is_the_same_as_asking_for_global(self, admin_api_client, url):
        default = admin_api_client.get(url)
        explicit = admin_api_client.get(url, {"scope": "global"})

        assert default.status_code == status.HTTP_200_OK
        assert default.data == explicit.data

    def test_rejects_an_unknown_scope(self, admin_api_client, url):
        response = admin_api_client.get(url, {"scope": "nonsense"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {"scope": ["Must be one of: global, data_set."]}

    def test_rows_expose_a_code_a_label_and_its_requirements_and_nothing_else(self, admin_api_client, url):
        response = admin_api_client.get(url)

        assert all(set(entity) == {"entity", "label", "permissions"} for entity in response.data)
        assert all(
            set(option) == {"code", "label", "requires"}
            for entity in response.data
            for option in entity["permissions"]
        )

    def test_labels_come_from_the_permission_row(self, admin_api_client, url):
        response = admin_api_client.get(url)

        labels = {option["code"]: option["label"] for entity in response.data for option in entity["permissions"]}

        assert labels[DATASET_ADD] == permission(PERMISSIONS.DATA_SET.ADD).name
        assert labels[DATASET_ADD] == "Create data sets"


class TestPermissionRequirements:
    """`requires` is the dependency map inverted - what one ticked box cannot be ticked without. The
    role editor checks it before submitting; the serializer enforces the same rule server-side."""

    def test_a_permission_names_what_it_cannot_be_granted_without(self, admin_api_client, url):
        requirements = _requirements(admin_api_client.get(url))

        assert requirements[DATASET_ROLE_ADD] == [DATASET_ROLE_VIEW]
        assert requirements[AGENT_ADD] == [AGENT_VIEW, DATASET_VIEW]
        assert requirements[DATASET_VIEW] == []

    def test_the_dataset_scope_drops_a_requirement_it_cannot_grant(self, admin_api_client, url):
        """`dataset.view` is global-only, so a dataset role's `agent.add` requires only `agent.view` -
        the same requirement `dependencies_within` drops for the validator."""
        requirements = _requirements(admin_api_client.get(url, {"scope": "data_set"}))

        assert requirements[AGENT_ADD] == [AGENT_VIEW]

    @pytest.mark.parametrize("scope", ["global", "data_set"])
    def test_every_requirement_is_itself_grantable_in_the_same_scope(self, admin_api_client, url, scope):
        """A requirement the editor cannot offer as a checkbox would be an error nobody can clear."""
        response = admin_api_client.get(url, {"scope": scope})
        served = _codes(response)

        required = {code for requires in _requirements(response).values() for code in requires}

        assert required <= served


class TestTheEditorReachesTheSameVerdictAsTheServer:
    def test_every_single_permission_is_judged_identically_on_both_sides(self, admin_api_client, url):
        requirements = _requirements(admin_api_client.get(url))

        for code in sorted(requirements):
            response = admin_api_client.post(
                reverse("global_role_list"), {"name": f"probe-{code}", "permissions": [code]}, format="json"
            )
            from_server = (
                response.data.get("missing_permissions", []) if response.status_code == status.HTTP_400_BAD_REQUEST
                else []
            )

            assert _unmet_requirements([code], requirements) == from_server, code


class TestPermissionListingAccess:
    def test_returns_401_when_unauthenticated(self, url):
        response = APIClient().get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_allows_a_global_role_view_holder(self, api_client, user, url):
        grant(user, PERMISSIONS.GLOBAL_ROLE.VIEW)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert DATASET_ADD in _codes(response)

    def test_allows_a_dataset_role_view_holder(self, api_client, user, url):
        grant(user, PERMISSIONS.DATA_SET_ROLE.VIEW)

        response = api_client.get(url, {"scope": "data_set"})

        assert response.status_code == status.HTTP_200_OK
        assert _codes(response) == DATASET_SCOPED_CONTRACT

    def test_denies_a_user_who_can_read_neither_kind_of_role(self, api_client, url):
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
