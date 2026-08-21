import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from account.authorization import PERMISSIONS
from account.models import User
from account.tests.helpers import client_for, grant

pytestmark = pytest.mark.django_db


@pytest.fixture
def url():
    return reverse("admin_list")


class TestListingAdmins:
    def test_requires_global_role_view(self, api_client, url):
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_a_global_role_view_holder_sees_who_holds_admin(self, user, url):
        grant(user, PERMISSIONS.GLOBAL_ROLE.VIEW)
        baker.make(User, email="admin@example.com", is_superuser=True)
        baker.make(User, email="bot@example.com", is_superuser=True, is_service_account=True)

        response = client_for(user).get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == [
            {
                "id": User.objects.get(email="admin@example.com").id,
                "email": "admin@example.com",
                "is_service_account": False,
            },
            {
                "id": User.objects.get(email="bot@example.com").id,
                "email": "bot@example.com",
                "is_service_account": True,
            },
        ]

    def test_excludes_accounts_without_admin(self, user, url):
        grant(user, PERMISSIONS.GLOBAL_ROLE.VIEW)
        baker.make(User, email="plain@example.com", is_superuser=False)

        response = client_for(user).get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "plain@example.com" not in [admin["email"] for admin in response.data]
