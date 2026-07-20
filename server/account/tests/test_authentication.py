import pytest
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed

from account.authentication import ServiceAccountTokenAuthentication
from account.models import User


@pytest.mark.django_db
class TestServiceAccountTokenAuthentication:
    def test_rejects_token_belonging_to_a_human_user(self):
        user = User.objects.create_user(email="jane@example.com", password="correct-horse")
        token = Token.objects.create(user=user)

        with pytest.raises(AuthenticationFailed):
            ServiceAccountTokenAuthentication().authenticate_credentials(token.key)

    def test_accepts_token_belonging_to_a_service_account(self):
        service_account = User.objects.create_service_account(email="svc@example.com")
        token = Token.objects.create(user=service_account)

        authenticated_user, authenticated_token = ServiceAccountTokenAuthentication().authenticate_credentials(
            token.key
        )

        assert authenticated_user == service_account
        assert authenticated_token == token
