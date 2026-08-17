import pytest
from django.urls import reverse
from rest_framework import status

from account.authorization import PUBLIC_CODES
from account.tests.public_permission_codes_contract import (
    DATASET_SCOPED_CONTRACT,
    PUBLIC_PERMISSION_CODES_CONTRACT,
)


def test_the_derived_vocabulary_matches_the_published_contract():
    """A failure here means the wire format moved. Update the contract module deliberately, and
    treat the diff as the frontend change it is - do not reach for `PUBLIC_CODES` to make it pass."""
    assert PUBLIC_CODES == PUBLIC_PERMISSION_CODES_CONTRACT


@pytest.mark.django_db
class TestThePermissionsEndpointServesTheContract:
    @pytest.fixture
    def url(self):
        return reverse("permission_list")

    def _codes(self, response) -> set[str]:
        return {option["code"] for entity in response.data for option in entity["permissions"]}

    def test_the_global_scope_serves_every_published_code(self, admin_api_client, url):
        response = admin_api_client.get(url, {"scope": "global"})

        assert response.status_code == status.HTTP_200_OK
        assert self._codes(response) == set(PUBLIC_PERMISSION_CODES_CONTRACT.values())

    def test_the_dataset_scope_serves_the_published_subset(self, admin_api_client, url):
        response = admin_api_client.get(url, {"scope": "dataset"})

        assert response.status_code == status.HTTP_200_OK
        assert self._codes(response) == set(DATASET_SCOPED_CONTRACT)
