from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIClient, APIRequestFactory

from account.authentication import AuthTokenAuthentication
from account.models import AuthToken, User


@pytest.mark.django_db
class TestAuthTokenAuthentication:
    def test_authenticates_via_header_with_non_expiring_token(self):
        user = User.objects.create_service_account(email="svc@example.com")
        token = AuthToken.objects.create(user=user, expires_at=None)
        request = APIRequestFactory().get("/", HTTP_AUTHORIZATION=f"Token {token.key}")

        authenticated_user, authenticated_token = AuthTokenAuthentication().authenticate(request)

        assert authenticated_user == user
        assert authenticated_token == token

    def test_authenticates_via_cookie_with_short_lived_token(self):
        user = User.objects.create_user(email="jane@example.com", password="irrelevant")
        token = AuthToken.objects.create(user=user, expires_at=timezone.now() + timedelta(minutes=5))
        request = APIRequestFactory().get("/")
        request.COOKIES["auth_token"] = token.key

        authenticated_user, _ = AuthTokenAuthentication().authenticate(request)

        assert authenticated_user == user

    def test_rejects_expired_token(self):
        user = User.objects.create_user(email="jane@example.com", password="irrelevant")
        token = AuthToken.objects.create(user=user, expires_at=timezone.now() - timedelta(minutes=1))
        request = APIRequestFactory().get("/")
        request.COOKIES["auth_token"] = token.key

        with pytest.raises(AuthenticationFailed):
            AuthTokenAuthentication().authenticate(request)

    def test_valid_token_slides_expiry_forward(self):
        user = User.objects.create_user(email="jane@example.com", password="irrelevant")
        token = AuthToken.objects.create(user=user, expires_at=timezone.now() + timedelta(minutes=1))
        request = APIRequestFactory().get("/")
        request.COOKIES["auth_token"] = token.key

        AuthTokenAuthentication().authenticate(request)

        token.refresh_from_db()
        assert token.expires_at > timezone.now() + timedelta(days=6)

    def test_never_expiring_token_is_not_slid(self):
        user = User.objects.create_service_account(email="svc@example.com")
        token = AuthToken.objects.create(user=user, expires_at=None)
        request = APIRequestFactory().get("/", HTTP_AUTHORIZATION=f"Token {token.key}")

        AuthTokenAuthentication().authenticate(request)

        token.refresh_from_db()
        assert token.expires_at is None

    def test_returns_none_when_no_credential_present(self):
        request = APIRequestFactory().get("/")

        assert AuthTokenAuthentication().authenticate(request) is None


@pytest.mark.django_db
class TestAuthTokenAuthenticationCsrf:
    def test_cookie_authenticated_mutating_request_without_csrf_token_is_rejected(self):
        user = User.objects.create_user(email="jane@example.com", password="irrelevant")
        token = AuthToken.objects.create(user=user, expires_at=timezone.now() + timedelta(minutes=5))
        client = APIClient(enforce_csrf_checks=True)
        client.cookies["auth_token"] = token.key

        response = client.post(reverse("logout"))

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cookie_authenticated_mutating_request_with_csrf_token_succeeds(self):
        user = User.objects.create_user(email="jane@example.com", password="irrelevant")
        token = AuthToken.objects.create(user=user, expires_at=timezone.now() + timedelta(minutes=5))
        client = APIClient(enforce_csrf_checks=True)
        client.cookies["auth_token"] = token.key
        csrf_response = client.get(reverse("csrf"))
        csrf_token = csrf_response.cookies["csrftoken"].value

        response = client.post(reverse("logout"), HTTP_X_CSRFTOKEN=csrf_token)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_header_authenticated_request_is_not_subject_to_csrf_check(self):
        user = User.objects.create_service_account(email="svc@example.com")
        token = AuthToken.objects.create(user=user, expires_at=None)
        client = APIClient(enforce_csrf_checks=True)

        response = client.get(reverse("account"), HTTP_AUTHORIZATION=f"Token {token.key}")

        assert response.status_code == status.HTTP_200_OK
