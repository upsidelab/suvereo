from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from account.models import AuthToken, User


@pytest.mark.django_db
class TestLoginView:
    def test_login_sets_auth_token_cookie_and_returns_no_token_in_body(self):
        User.objects.create_user(email="jane@example.com", password="correct-horse")
        client = APIClient()

        response = client.post(
            reverse("login"), {"email": "jane@example.com", "password": "correct-horse"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert "auth_token" in response.cookies
        assert "token" not in response.data
        assert response.data["email"] == "jane@example.com"

        token = AuthToken.objects.get(key=response.cookies["auth_token"].value)
        assert token.expires_at is not None
        assert token.expires_at > timezone.now()

    def test_login_with_wrong_password_is_forbidden(self):
        User.objects.create_user(email="jane@example.com", password="correct-horse")
        client = APIClient()

        response = client.post(
            reverse("login"), {"email": "jane@example.com", "password": "wrong"}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "auth_token" not in response.cookies


@pytest.mark.django_db
class TestLoginViewCsrf:
    def test_login_without_csrf_token_is_rejected(self):
        User.objects.create_user(email="jane@example.com", password="correct-horse")
        client = APIClient(enforce_csrf_checks=True)

        response = client.post(
            reverse("login"), {"email": "jane@example.com", "password": "correct-horse"}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_login_with_csrf_token_succeeds(self):
        User.objects.create_user(email="jane@example.com", password="correct-horse")
        client = APIClient(enforce_csrf_checks=True)
        csrf_response = client.get(reverse("csrf"))
        csrf_token = csrf_response.cookies["csrftoken"].value

        response = client.post(
            reverse("login"),
            {"email": "jane@example.com", "password": "correct-horse"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestLogoutView:
    def test_logout_deletes_the_token_and_a_stale_cookie_is_rejected(self):
        User.objects.create_user(email="jane@example.com", password="correct-horse")
        client = APIClient()
        client.post(reverse("login"), {"email": "jane@example.com", "password": "correct-horse"}, format="json")

        assert client.get(reverse("account")).status_code == status.HTTP_200_OK

        logout_response = client.post(reverse("logout"))
        assert logout_response.status_code == status.HTTP_204_NO_CONTENT

        assert client.get(reverse("account")).status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAuthTokenSlidingExpiryViaLoginFlow:
    def test_valid_request_extends_expiry(self):
        user = User.objects.create_user(email="jane@example.com", password="irrelevant")
        token = AuthToken.objects.create(user=user, expires_at=timezone.now() + timedelta(minutes=1))
        client = APIClient()
        client.cookies["auth_token"] = token.key

        client.get(reverse("account"))

        token.refresh_from_db()
        assert token.expires_at > timezone.now() + timedelta(days=6)


@pytest.mark.django_db
class TestCsrfView:
    def test_csrf_endpoint_sets_csrf_cookie(self):
        client = APIClient()

        response = client.get(reverse("csrf"))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert "csrftoken" in response.cookies
