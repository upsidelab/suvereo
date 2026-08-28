import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.tests.helpers import grant, permission
from account.tests.public_permission_codes_contract import DATASET_ADD, DATASET_SCOPED_CONTRACT

pytestmark = pytest.mark.django_db


@pytest.fixture
def url():
    return reverse("permission_list")


def _codes(response) -> set[str]:
    return {option["code"] for entity in response.data for option in entity["permissions"]}


class TestPermissionListing:
    def test_omitting_the_scope_is_the_same_as_asking_for_global(self, admin_api_client, url):
        default = admin_api_client.get(url)
        explicit = admin_api_client.get(url, {"scope": "global"})

        assert default.status_code == status.HTTP_200_OK
        assert default.data == explicit.data

    def test_rejects_an_unknown_scope(self, admin_api_client, url):
        response = admin_api_client.get(url, {"scope": "nonsense"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {"scope": ["Must be one of: global, dataset."]}

    def test_rows_expose_a_code_and_a_label_and_nothing_else(self, admin_api_client, url):
        response = admin_api_client.get(url)

        assert all(set(entity) == {"entity", "label", "permissions"} for entity in response.data)
        assert all(set(option) == {"code", "label"} for entity in response.data for option in entity["permissions"])

    def test_labels_come_from_the_permission_row(self, admin_api_client, url):
        response = admin_api_client.get(url)

        labels = {option["code"]: option["label"] for entity in response.data for option in entity["permissions"]}

        assert labels[DATASET_ADD] == permission(PERMISSIONS.DATASET.ADD).name
        assert labels[DATASET_ADD] == "Create data sets"


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
        grant(user, PERMISSIONS.DATASET_ROLE.VIEW)

        response = api_client.get(url, {"scope": "dataset"})

        assert response.status_code == status.HTTP_200_OK
        assert _codes(response) == DATASET_SCOPED_CONTRACT

    def test_denies_a_user_who_can_read_neither_kind_of_role(self, api_client, url):
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
