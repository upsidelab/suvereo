import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.models import User
from account.services import ServiceAccountNameService
from account.tests.helpers import grant

pytestmark = pytest.mark.django_db


def _client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def service_account():
    return baker.make(User, is_service_account=True, is_superuser=False)


class TestServiceAccountListView:
    @pytest.fixture
    def url(self):
        return reverse("service_account_list")

    @pytest.fixture
    def payload(self):
        return {"name": "reporting-bot", "is_active": True, "is_admin": False}

    def test_returns_401_when_unauthenticated(self, url):
        response = APIClient().get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_can_list_service_accounts(self, admin_api_client, service_account, url):
        response = admin_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_user_without_any_service_account_permission_cannot_list_them(self, api_client, url):
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_view_serviceaccount_holder_can_list_them(self, api_client, user, service_account, url):
        grant(user, PERMISSIONS.SERVICE_ACCOUNT.VIEW)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert service_account.id in [result["id"] for result in response.data["results"]]

    def test_internal_service_accounts_are_not_listed(self, admin_api_client, service_account, url):
        internal = User.objects.create_service_account("internal@example.com", is_internal=True)

        response = admin_api_client.get(url)

        ids = [result["id"] for result in response.data["results"]]
        assert service_account.id in ids
        assert internal.id not in ids

    def test_view_serviceaccount_holder_cannot_create_one(self, api_client, user, url, payload):
        grant(user, PERMISSIONS.SERVICE_ACCOUNT.VIEW)

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not User.objects.filter(is_service_account=True).exists()

    def test_add_serviceaccount_holder_can_create_one(self, api_client, user, url, payload):
        grant(user, PERMISSIONS.SERVICE_ACCOUNT.ADD)

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(is_service_account=True).exists()

    def test_create_response_carries_the_new_accounts_id_and_token(self, admin_api_client, url, payload):
        response = admin_api_client.post(url, payload, format="json")

        created = User.objects.get(is_service_account=True)
        assert response.data["id"] == created.id
        assert response.data["token"] == Token.objects.get(user=created).key

    def test_duplicate_name_is_rejected_with_400(self, admin_api_client, url, payload):
        admin_api_client.post(url, payload, format="json")

        response = admin_api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "name" in response.data
        assert User.objects.filter(is_service_account=True).count() == 1

    def test_create_response_names_the_admin_flag_is_admin_never_is_superuser(
        self, admin_api_client, url, payload
    ):
        response = admin_api_client.post(url, payload, format="json")

        assert "is_superuser" not in response.data
        assert response.data["is_admin"] is False


class TestServiceAccountView:
    @pytest.fixture
    def url(self, service_account):
        return f"/api/service_accounts/{service_account.id}"

    @pytest.fixture
    def payload(self):
        return {"name": "renamed-bot", "is_active": True, "is_admin": False}

    def test_user_without_change_serviceaccount_cannot_update_one(self, api_client, url, payload):
        response = api_client.patch(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_view_serviceaccount_holder_cannot_update_one(self, api_client, user, url, payload):
        grant(user, PERMISSIONS.SERVICE_ACCOUNT.VIEW)

        response = api_client.patch(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_change_serviceaccount_holder_can_update_one(self, api_client, user, service_account, url, payload):
        grant(user, PERMISSIONS.SERVICE_ACCOUNT.CHANGE)

        response = api_client.patch(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == service_account.id
        service_account.refresh_from_db()
        assert service_account.email.startswith("renamed-bot@")

    def test_renaming_onto_another_accounts_name_is_rejected_with_400(self, admin_api_client, url, payload):
        admin_api_client.post(
            reverse("service_account_list"), {"name": "renamed-bot", "is_active": True, "is_admin": False},
            format="json",
        )

        response = admin_api_client.patch(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "name" in response.data

    def test_an_account_can_be_saved_under_the_name_it_already_has(self, admin_api_client, service_account):
        created = admin_api_client.post(
            reverse("service_account_list"), {"name": "keeps-name", "is_active": True, "is_admin": False},
            format="json",
        )

        response = admin_api_client.patch(
            f"/api/service_accounts/{created.data['id']}",
            {"name": "keeps-name", "is_active": False, "is_admin": False},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

    def test_patch_updates_only_the_fields_it_was_given(self, admin_api_client, service_account, url):
        original_email = service_account.email

        response = admin_api_client.patch(url, {"is_active": False}, format="json")

        assert response.status_code == status.HTTP_200_OK
        service_account.refresh_from_db()
        assert service_account.email == original_email
        assert service_account.is_active is False


class TestResetTokenView:
    @pytest.fixture
    def url(self, service_account):
        return reverse("reset_token", kwargs={"id": service_account.id})

    def test_user_without_change_serviceaccount_cannot_reset_a_token(self, api_client, service_account, url):
        original = Token.objects.create(user=service_account)

        response = api_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Token.objects.get(user=service_account).key == original.key

    def test_view_serviceaccount_holder_cannot_reset_a_token(self, api_client, user, url):
        grant(user, PERMISSIONS.SERVICE_ACCOUNT.VIEW)

        response = api_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_change_serviceaccount_holder_can_reset_a_token(self, api_client, user, service_account, url):
        original = Token.objects.create(user=service_account)
        grant(user, PERMISSIONS.SERVICE_ACCOUNT.CHANGE)

        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["token"] != original.key


class TestCheckServiceNameView:
    @pytest.fixture
    def url(self):
        return reverse("check_service_name")

    def test_user_holding_neither_add_nor_change_cannot_check_a_name(self, api_client, url):
        response = api_client.post(url, {"name": "reporting-bot"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize(
        "codename", [PERMISSIONS.SERVICE_ACCOUNT.ADD, PERMISSIONS.SERVICE_ACCOUNT.CHANGE]
    )
    def test_either_add_or_change_alone_is_enough_to_check_a_name(self, api_client, user, url, codename):
        grant(user, codename)

        response = api_client.post(url, {"name": "reporting-bot"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_available"] is True

    def test_view_serviceaccount_alone_is_not_enough(self, api_client, user, url):
        grant(user, PERMISSIONS.SERVICE_ACCOUNT.VIEW)

        response = api_client.post(url, {"name": "reporting-bot"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestOnlyAdminsManageAdminServiceAccounts:
    @pytest.fixture
    def service_account_manager(self, user):
        grant(user, *PERMISSIONS.SERVICE_ACCOUNT)
        return user

    @pytest.fixture
    def admin_service_account(self):
        return baker.make(User, is_service_account=True, is_superuser=True, is_active=True)

    def test_non_admin_cannot_create_an_admin_service_account(self, api_client, service_account_manager):
        response = api_client.post(
            reverse("service_account_list"),
            {"name": "sneaky-bot", "is_active": True, "is_admin": True},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not User.objects.filter(is_service_account=True).exists()

    def test_non_admin_can_still_create_an_ordinary_service_account(self, api_client, service_account_manager):
        response = api_client.post(
            reverse("service_account_list"),
            {"name": "ordinary-bot", "is_active": True, "is_admin": False},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_non_admin_cannot_promote_a_service_account(self, api_client, service_account_manager):
        target = baker.make(User, is_service_account=True, is_superuser=False)

        response = api_client.patch(f"/api/service_accounts/{target.id}", {"is_admin": True}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        target.refresh_from_db()
        assert target.is_superuser is False

    def test_non_admin_cannot_revoke_or_deactivate_an_admin_service_account(
        self, api_client, service_account_manager, admin_service_account
    ):
        revoke = api_client.patch(
            f"/api/service_accounts/{admin_service_account.id}", {"is_admin": False}, format="json"
        )
        deactivate = api_client.patch(
            f"/api/service_accounts/{admin_service_account.id}", {"is_active": False}, format="json"
        )

        assert revoke.status_code == status.HTTP_403_FORBIDDEN
        assert deactivate.status_code == status.HTTP_403_FORBIDDEN
        admin_service_account.refresh_from_db()
        assert admin_service_account.is_superuser is True
        assert admin_service_account.is_active is True

    def test_non_admin_cannot_reset_an_admin_service_accounts_token(
        self, api_client, service_account_manager, admin_service_account
    ):
        original = Token.objects.create(user=admin_service_account)

        response = api_client.post(reverse("reset_token", kwargs={"id": admin_service_account.id}))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Token.objects.get(user=admin_service_account).key == original.key

    def test_non_admin_can_still_reset_an_ordinary_service_accounts_token(
        self, api_client, service_account_manager, service_account
    ):
        Token.objects.create(user=service_account)

        response = api_client.post(reverse("reset_token", kwargs={"id": service_account.id}))

        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_do_all_of_it(self, admin_api_client, admin_service_account):
        create = admin_api_client.post(
            reverse("service_account_list"),
            {"name": "new-admin-bot", "is_active": True, "is_admin": True},
            format="json",
        )
        revoke = admin_api_client.patch(
            f"/api/service_accounts/{admin_service_account.id}", {"is_admin": False}, format="json"
        )

        assert create.status_code == status.HTTP_201_CREATED
        email = ServiceAccountNameService().generate_service_account_email("new-admin-bot")
        assert User.objects.get(email=email).is_superuser is True
        assert revoke.status_code == status.HTTP_200_OK
        admin_service_account.refresh_from_db()
        assert admin_service_account.is_superuser is False


class TestUserAndServiceAccountPermissionsAreIndependent:
    """Phase 7's core claim: the two entities live on one model but grant separately."""

    @pytest.fixture
    def user_manager(self):
        manager = baker.make(User, is_service_account=False, is_superuser=False)
        grant(manager, *PERMISSIONS.USER)
        return manager

    @pytest.fixture
    def service_account_manager(self):
        manager = baker.make(User, is_service_account=False, is_superuser=False)
        grant(manager, *PERMISSIONS.SERVICE_ACCOUNT)
        return manager

    def test_full_user_permissions_grant_no_service_account_access(self, user_manager, service_account):
        client = _client_for(user_manager)

        assert client.get(reverse("service_account_list")).status_code == status.HTTP_403_FORBIDDEN
        assert (
            client.patch(
                f"/api/service_accounts/{service_account.id}",
                {"name": "renamed-bot", "is_active": True, "is_admin": False},
                format="json",
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )
        assert (
            client.post(reverse("reset_token", kwargs={"id": service_account.id})).status_code
            == status.HTTP_403_FORBIDDEN
        )

    def test_full_service_account_permissions_grant_no_user_access(self, service_account_manager):
        client = _client_for(service_account_manager)
        managed_user = baker.make(User, is_service_account=False)

        assert client.get(reverse("user_list")).status_code == status.HTTP_403_FORBIDDEN
        assert (
            client.patch(
                reverse("user_details", kwargs={"id": managed_user.id}),
                {"email": "renamed@example.com", "is_active": True, "is_admin": False},
                format="json",
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

    def test_service_account_manager_can_still_manage_service_accounts(self, service_account_manager, service_account):
        client = _client_for(service_account_manager)

        assert client.get(reverse("service_account_list")).status_code == status.HTTP_200_OK

    def test_user_manager_can_still_manage_users(self, user_manager):
        client = _client_for(user_manager)

        assert client.get(reverse("user_list")).status_code == status.HTTP_200_OK
