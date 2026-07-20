import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from account.models import User


@pytest.mark.django_db
class TestLoginView:
    def test_login_establishes_session_and_returns_no_token(self):
        User.objects.create_user(email="jane@example.com", password="correct-horse")
        client = APIClient()

        response = client.post(
            reverse("login"), {"email": "jane@example.com", "password": "correct-horse"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert "sessionid" in response.cookies
        assert "token" not in response.data
        assert response.data["email"] == "jane@example.com"

    def test_login_with_wrong_password_is_forbidden(self):
        User.objects.create_user(email="jane@example.com", password="correct-horse")
        client = APIClient()

        response = client.post(
            reverse("login"), {"email": "jane@example.com", "password": "wrong"}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "sessionid" not in response.cookies


@pytest.mark.django_db
class TestLogoutView:
    def test_logout_invalidates_the_session(self):
        User.objects.create_user(email="jane@example.com", password="correct-horse")
        client = APIClient()
        client.post(reverse("login"), {"email": "jane@example.com", "password": "correct-horse"}, format="json")

        assert client.get(reverse("account")).status_code == status.HTTP_200_OK

        logout_response = client.post(reverse("logout"))
        assert logout_response.status_code == status.HTTP_204_NO_CONTENT

        assert client.get(reverse("account")).status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestCsrfView:
    def test_csrf_endpoint_sets_csrf_cookie(self):
        client = APIClient()

        response = client.get(reverse("csrf"))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert "csrftoken" in response.cookies
