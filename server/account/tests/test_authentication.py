from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

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
