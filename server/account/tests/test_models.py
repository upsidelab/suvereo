from datetime import timedelta

import pytest
from django.utils import timezone

from account.models import AuthToken, User


@pytest.mark.django_db
class TestAuthTokenIsExpired:
    def test_none_expiry_is_never_expired(self):
        user = User.objects.create_service_account(email="svc@example.com")
        token = AuthToken.objects.create(user=user, expires_at=None)

        assert token.is_expired() is False

    def test_future_expiry_is_not_expired(self):
        user = User.objects.create_user(email="jane@example.com", password="irrelevant")
        token = AuthToken.objects.create(user=user, expires_at=timezone.now() + timedelta(minutes=5))

        assert token.is_expired() is False

    def test_past_expiry_is_expired(self):
        user = User.objects.create_user(email="jane@example.com", password="irrelevant")
        token = AuthToken.objects.create(user=user, expires_at=timezone.now() - timedelta(minutes=1))

        assert token.is_expired() is True
