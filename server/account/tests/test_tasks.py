from datetime import timedelta

import pytest
from django.utils import timezone

from account.models import AuthToken, User
from account.tasks import clean_expired_auth_tokens


@pytest.mark.django_db
class TestCleanExpiredAuthTokens:
    def test_deletes_expired_tokens(self):
        user = User.objects.create_user(email="jane@example.com", password="irrelevant")
        expired_token = AuthToken.objects.create(user=user, expires_at=timezone.now() - timedelta(minutes=1))

        clean_expired_auth_tokens()

        assert not AuthToken.objects.filter(id=expired_token.id).exists()

    def test_keeps_valid_non_expired_tokens(self):
        user = User.objects.create_user(email="jane@example.com", password="irrelevant")
        valid_token = AuthToken.objects.create(user=user, expires_at=timezone.now() + timedelta(minutes=5))

        clean_expired_auth_tokens()

        assert AuthToken.objects.filter(id=valid_token.id).exists()

    def test_keeps_never_expiring_service_account_tokens(self):
        service_account = User.objects.create_service_account(email="svc@example.com")
        token = AuthToken.objects.create(user=service_account, expires_at=None)

        clean_expired_auth_tokens()

        assert AuthToken.objects.filter(id=token.id).exists()
