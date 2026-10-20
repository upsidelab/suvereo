import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from account.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def human_user():
    user = baker.make(User, is_service_account=False, is_superuser=False)
    user.set_password("old-password")
    user.save()
    return user


@pytest.fixture
def refresh_token(human_user):
    return RefreshToken.for_user(human_user)


def _bearer_client(access_token) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
    return client


def _refresh(refresh_token):
    return APIClient().post(reverse("token_refresh"), {"refresh": str(refresh_token)}, format="json")


class TestLogin:
    @pytest.fixture
    def url(self):
        return reverse("login")

    def test_returns_a_token_pair(self, human_user, url):
        response = APIClient().post(url, {"email": human_user.email, "password": "old-password"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert {"access", "refresh"} <= response.data.keys()
        assert _bearer_client(response.data["access"]).get(reverse("account")).status_code == status.HTTP_200_OK

    def test_does_not_issue_an_api_key(self, human_user, url):
        APIClient().post(url, {"email": human_user.email, "password": "old-password"}, format="json")

        assert not Token.objects.filter(user=human_user).exists()

    def test_wrong_password_is_rejected(self, human_user, url):
        response = APIClient().post(url, {"email": human_user.email, "password": "wrong"}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inactive_user_is_rejected(self, human_user, url):
        human_user.is_active = False
        human_user.save()

        response = APIClient().post(url, {"email": human_user.email, "password": "old-password"}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthentication:
    def test_access_token_authenticates(self, refresh_token):
        response = _bearer_client(refresh_token.access_token).get(reverse("account"))

        assert response.status_code == status.HTTP_200_OK

    def test_api_key_still_authenticates(self, human_user):
        token = Token.objects.create(user=human_user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = client.get(reverse("account"))

        assert response.status_code == status.HTTP_200_OK

    def test_malformed_access_token_is_rejected(self):
        response = _bearer_client("not-a-jwt").get(reverse("account"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_deactivated_user_access_token_is_rejected(self, human_user, refresh_token):
        human_user.is_active = False
        human_user.save()

        response = _bearer_client(refresh_token.access_token).get(reverse("account"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenRefresh:
    def test_returns_a_new_pair(self, refresh_token):
        response = _refresh(refresh_token)

        assert response.status_code == status.HTTP_200_OK
        assert {"access", "refresh"} <= response.data.keys()
        assert response.data["refresh"] != str(refresh_token)

    def test_rotated_refresh_token_is_rejected(self, refresh_token):
        _refresh(refresh_token)

        response = _refresh(refresh_token)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_rotated_refresh_token_can_be_refreshed(self, refresh_token):
        rotated = _refresh(refresh_token).data["refresh"]

        response = _refresh(rotated)

        assert response.status_code == status.HTTP_200_OK

    def test_deleted_user_refresh_token_is_rejected(self, human_user, refresh_token):
        human_user.delete()

        response = _refresh(refresh_token)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_deactivated_user_refresh_token_is_rejected(self, human_user, refresh_token):
        human_user.is_active = False
        human_user.save()

        response = _refresh(refresh_token)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogout:
    def test_blacklists_the_refresh_token(self, refresh_token):
        response = APIClient().post(reverse("logout"), {"refresh": str(refresh_token)}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert _refresh(refresh_token).status_code == status.HTTP_401_UNAUTHORIZED


class TestPasswordChange:
    @pytest.fixture
    def change_password(self, admin_api_client, human_user):
        def change():
            response = admin_api_client.put(
                reverse("user_password", kwargs={"id": human_user.id}), {"password": "new-password"}, format="json"
            )
            assert response.status_code == status.HTTP_200_OK

        return change

    def test_revokes_refresh_tokens(self, refresh_token, change_password):
        change_password()

        assert _refresh(refresh_token).status_code == status.HTTP_401_UNAUTHORIZED

    def test_revokes_access_tokens(self, refresh_token, change_password):
        access_token = refresh_token.access_token

        change_password()

        assert _bearer_client(access_token).get(reverse("account")).status_code == status.HTTP_401_UNAUTHORIZED

    def test_leaves_other_users_sessions_intact(self, admin_user, change_password):
        other_refresh_token = RefreshToken.for_user(admin_user)

        change_password()

        assert _refresh(other_refresh_token).status_code == status.HTTP_200_OK
