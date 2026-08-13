import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import PERMISSIONS
from account.models import User

pytestmark = pytest.mark.django_db


def _permission(codename: str) -> Permission:
    app_label, name = codename.split(".")
    return Permission.objects.get(codename=name, content_type__app_label=app_label)


def _client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def target_user():
    return baker.make(User, is_service_account=False, is_superuser=False)


class TestUserListView:
    @pytest.fixture
    def url(self):
        return reverse("user_list")

    @pytest.fixture
    def payload(self):
        return {"email": "new@example.com", "password": "s3cret-pass", "is_active": True, "is_admin": False}

    def test_returns_401_when_unauthenticated(self, url):
        response = APIClient().get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_can_list_users(self, admin_api_client, target_user, url):
        response = admin_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_user_without_any_user_permission_cannot_list_users(self, api_client, url):
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_view_user_holder_can_list_users(self, api_client, user, target_user, url):
        user.user_permissions.add(_permission(PERMISSIONS.USER.VIEW))

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert target_user.id in [result["id"] for result in response.data["results"]]

    def test_view_user_holder_cannot_create_users(self, api_client, user, url, payload):
        user.user_permissions.add(_permission(PERMISSIONS.USER.VIEW))

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not User.objects.filter(email="new@example.com").exists()

    def test_add_user_holder_can_create_a_user(self, api_client, user, url, payload):
        user.user_permissions.add(_permission(PERMISSIONS.USER.ADD))

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email="new@example.com").exists()

    def test_create_response_carries_the_new_users_id(self, api_client, user, url, payload):
        user.user_permissions.add(_permission(PERMISSIONS.USER.ADD))

        response = api_client.post(url, payload, format="json")

        assert response.data["id"] == User.objects.get(email="new@example.com").id

    def test_add_user_holder_cannot_list_users(self, api_client, url, user):
        user.user_permissions.add(_permission(PERMISSIONS.USER.ADD))

        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_permission_granted_through_a_group_is_honoured(self, api_client, user, url):
        group = baker.make("auth.Group")
        group.permissions.add(_permission(PERMISSIONS.USER.VIEW))
        user.groups.add(group)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK


class TestUserView:
    @pytest.fixture
    def url(self, target_user):
        return reverse("user_details", kwargs={"id": target_user.id})

    @pytest.fixture
    def payload(self):
        return {"email": "renamed@example.com", "is_active": True, "is_admin": False}

    def test_returns_401_when_unauthenticated(self, url, payload):
        response = APIClient().patch(url, payload, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_can_update_a_user(self, admin_api_client, target_user, url, payload):
        response = admin_api_client.patch(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        target_user.refresh_from_db()
        assert target_user.email == "renamed@example.com"

    def test_user_without_change_user_cannot_update_a_user(self, api_client, target_user, url, payload):
        response = api_client.patch(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        target_user.refresh_from_db()
        assert target_user.email != "renamed@example.com"

    def test_view_user_holder_cannot_update_a_user(self, api_client, user, target_user, url, payload):
        user.user_permissions.add(_permission(PERMISSIONS.USER.VIEW))

        response = api_client.patch(url, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_change_user_holder_can_update_a_user(self, api_client, user, target_user, url, payload):
        user.user_permissions.add(_permission(PERMISSIONS.USER.CHANGE))

        response = api_client.patch(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        target_user.refresh_from_db()
        assert target_user.email == "renamed@example.com"

    def test_patch_updates_only_the_fields_it_was_given(self, admin_api_client, target_user, url):
        target_user.is_active = True
        target_user.is_superuser = True
        target_user.save()

        response = admin_api_client.patch(url, {"email": "only-email@example.com"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        target_user.refresh_from_db()
        assert target_user.email == "only-email@example.com"
        assert target_user.is_active is True
        assert target_user.is_superuser is True

    def test_put_still_requires_every_field(self, admin_api_client, url):
        response = admin_api_client.put(url, {"email": "only-email@example.com"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "is_active" in response.data
        assert "is_admin" in response.data

    def test_update_response_reflects_the_saved_values_not_the_previous_ones(
        self, admin_api_client, target_user, url
    ):
        response = admin_api_client.patch(
            url, {"email": "fresh@example.com", "is_active": False, "is_admin": True}, format="json"
        )

        assert response.data == {
            "id": target_user.id,
            "email": "fresh@example.com",
            "is_active": False,
            "is_admin": True,
        }


class TestOnlyAdminsManageAdmins:
    """A holder of account.* codenames who is not themselves an admin must not be able to reach
    admin through them."""

    @pytest.fixture
    def user_manager(self, user):
        user.user_permissions.set(
            [
                _permission(PERMISSIONS.USER.VIEW),
                _permission(PERMISSIONS.USER.ADD),
                _permission(PERMISSIONS.USER.CHANGE),
            ]
        )
        return user

    @pytest.fixture
    def admin_target(self):
        return baker.make(User, is_service_account=False, is_superuser=True, is_active=True)

    def test_non_admin_cannot_create_an_admin(self, api_client, user_manager):
        payload = {"email": "sneaky@example.com", "password": "pw123456", "is_active": True, "is_admin": True}

        response = api_client.post(reverse("user_list"), payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not User.objects.filter(email="sneaky@example.com").exists()

    def test_non_admin_can_still_create_an_ordinary_user(self, api_client, user_manager):
        payload = {"email": "ordinary@example.com", "password": "pw123456", "is_active": True, "is_admin": False}

        response = api_client.post(reverse("user_list"), payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED

    def test_non_admin_cannot_promote_another_user_to_admin(self, api_client, user_manager, target_user):
        response = api_client.patch(
            reverse("user_details", kwargs={"id": target_user.id}),
            {"email": target_user.email, "is_active": True, "is_admin": True},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        target_user.refresh_from_db()
        assert target_user.is_superuser is False

    def test_non_admin_cannot_promote_themselves(self, api_client, user_manager):
        response = api_client.patch(
            reverse("user_details", kwargs={"id": user_manager.id}),
            {"email": user_manager.email, "is_active": True, "is_admin": True},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        user_manager.refresh_from_db()
        assert user_manager.is_superuser is False

    def test_non_admin_cannot_revoke_admin(self, api_client, user_manager, admin_target):
        response = api_client.patch(
            reverse("user_details", kwargs={"id": admin_target.id}),
            {"email": admin_target.email, "is_active": True, "is_admin": False},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        admin_target.refresh_from_db()
        assert admin_target.is_superuser is True

    def test_non_admin_cannot_deactivate_an_admin(self, api_client, user_manager, admin_target):
        response = api_client.patch(
            reverse("user_details", kwargs={"id": admin_target.id}), {"is_active": False}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        admin_target.refresh_from_db()
        assert admin_target.is_active is True

    def test_non_admin_cannot_reset_an_admins_password(self, api_client, user_manager, admin_target):
        response = api_client.put(
            reverse("user_password", kwargs={"id": admin_target.id}), {"password": "hijacked"}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        admin_target.refresh_from_db()
        assert not admin_target.check_password("hijacked")

    def test_non_admin_cannot_change_an_admins_email(self, api_client, user_manager, admin_target):
        response = api_client.patch(
            reverse("user_details", kwargs={"id": admin_target.id}),
            {"email": "hijacked@example.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_do_all_of_it(self, admin_api_client, admin_target):
        create = admin_api_client.post(
            reverse("user_list"),
            {"email": "new-admin@example.com", "password": "pw123456", "is_active": True, "is_admin": True},
            format="json",
        )
        revoke = admin_api_client.patch(
            reverse("user_details", kwargs={"id": admin_target.id}),
            {"email": admin_target.email, "is_active": False, "is_admin": False},
            format="json",
        )

        assert create.status_code == status.HTTP_201_CREATED
        assert User.objects.get(email="new-admin@example.com").is_superuser is True
        assert revoke.status_code == status.HTTP_200_OK
        admin_target.refresh_from_db()
        assert admin_target.is_superuser is False
        assert admin_target.is_active is False


class TestUserPasswordView:
    @pytest.fixture
    def url(self, target_user):
        return reverse("user_password", kwargs={"id": target_user.id})

    def test_change_user_holder_can_set_a_password(self, api_client, user, target_user, url):
        user.user_permissions.add(_permission(PERMISSIONS.USER.CHANGE))

        response = api_client.put(url, {"password": "brand-new-pass"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"id": target_user.id}
        target_user.refresh_from_db()
        assert target_user.check_password("brand-new-pass")

    def test_view_user_holder_cannot_set_a_password(self, api_client, user, target_user, url):
        user.user_permissions.add(_permission(PERMISSIONS.USER.VIEW))

        response = api_client.put(url, {"password": "brand-new-pass"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        target_user.refresh_from_db()
        assert not target_user.check_password("brand-new-pass")
