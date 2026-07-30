import pytest
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import ADMIN_GROUP_NAME, is_application_admin
from account.models import User


def _api_client_with_permission(codename):
    """Build an APIClient authenticated as a plain (non-Admin-group) user holding the given
    account-app permission directly, mirroring how a delegable permission would be granted.
    """
    actor = baker.make(User, is_service_account=False)
    actor.user_permissions.add(Permission.objects.get(content_type__app_label="account", codename=codename))
    actor = User.objects.get(pk=actor.pk)  # avoid a stale permission cache on the in-memory instance
    client = APIClient()
    client.force_authenticate(user=actor)
    return client, actor


@pytest.mark.django_db
class TestUserListView:
    def test_admin_group_member_can_list_users(self, admin_api_client):
        response = admin_api_client.get(reverse("user_list"))
        assert response.status_code == status.HTTP_200_OK

    def test_regular_user_cannot_list_users(self, api_client):
        response = api_client.get(reverse("user_list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_staff_only_user_cannot_list_users(self):
        staff_only = baker.make(User, is_staff=True)
        client = APIClient()
        client.force_authenticate(user=staff_only)
        response = client.get(reverse("user_list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_listed_users_expose_is_admin_and_group_ids(self, admin_api_client, admin_user):
        response = admin_api_client.get(reverse("user_list"))
        by_id = {item["id"]: item for item in response.data["results"]}
        assert by_id[admin_user.id]["is_admin"] is True
        admin_group_id = Group.objects.get(name=ADMIN_GROUP_NAME).id
        assert by_id[admin_user.id]["group_ids"] == [admin_group_id]
        assert "is_staff" not in by_id[admin_user.id]

    def test_create_user_with_admin_group_id_adds_group_membership(self, admin_api_client):
        admin_group_id = Group.objects.get(name=ADMIN_GROUP_NAME).id
        payload = {
            "email": "new-admin@example.com",
            "password": "s3cret!",
            "is_active": True,
            "group_ids": [admin_group_id],
        }
        response = admin_api_client.post(reverse("user_list"), payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email="new-admin@example.com")
        assert is_application_admin(user) is True
        assert user.is_staff is False

    def test_create_user_with_no_groups(self, admin_api_client):
        payload = {"email": "regular@example.com", "password": "s3cret!", "is_active": True, "group_ids": []}
        admin_api_client.post(reverse("user_list"), payload, format="json")
        user = User.objects.get(email="regular@example.com")
        assert is_application_admin(user) is False


@pytest.mark.django_db
class TestUserUpdateView:
    def test_update_toggles_admin_group_membership(self, admin_api_client):
        user = baker.make(User, is_service_account=False)
        admin_group_id = Group.objects.get(name=ADMIN_GROUP_NAME).id
        url = reverse("user_details", kwargs={"id": user.id})

        response = admin_api_client.put(
            url, {"email": user.email, "is_active": True, "group_ids": [admin_group_id]}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert is_application_admin(User.objects.get(pk=user.pk)) is True

        admin_api_client.put(url, {"email": user.email, "is_active": True, "group_ids": []}, format="json")
        assert is_application_admin(User.objects.get(pk=user.pk)) is False

    def test_update_does_not_touch_is_staff(self, admin_api_client):
        user = baker.make(User, is_service_account=False, is_staff=False)
        url = reverse("user_details", kwargs={"id": user.id})
        admin_api_client.put(url, {"email": user.email, "is_active": True, "group_ids": []}, format="json")
        assert User.objects.get(pk=user.pk).is_staff is False

    def test_update_response_exposes_is_admin_and_group_ids(self, admin_api_client):
        user = baker.make(User, is_service_account=False)
        admin_group_id = Group.objects.get(name=ADMIN_GROUP_NAME).id
        url = reverse("user_details", kwargs={"id": user.id})

        response = admin_api_client.put(
            url, {"email": user.email, "is_active": True, "group_ids": [admin_group_id]}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == user.id
        assert response.data["is_admin"] is True
        assert response.data["group_ids"] == [admin_group_id]


@pytest.mark.django_db
class TestGroupIdsPrivilegeEscalationGuard:
    """Regression tests: `manage_users` is a delegable permission, so holding it must never be
    enough to grant Admin-equivalent group membership (the Admin group itself, or any group
    that grants `manage_users`/`manage_service_accounts`) — only literal Admin-group members
    may do that. See account.authorization.assert_group_ids_assignable.
    """

    def test_manage_users_holder_cannot_self_promote_via_group_ids(self):
        client, actor = _api_client_with_permission("manage_users")
        admin_group_id = Group.objects.get(name=ADMIN_GROUP_NAME).id

        response = client.patch(
            reverse("user_details", kwargs={"id": actor.id}),
            {"email": actor.email, "is_active": True, "group_ids": [admin_group_id]},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert is_application_admin(User.objects.get(pk=actor.pk)) is False

    def test_manage_users_holder_cannot_assign_a_group_that_itself_grants_manage_users(self):
        client, actor = _api_client_with_permission("manage_users")
        sensitive_group = Group.objects.create(name="Sensitive")
        sensitive_group.permissions.add(
            Permission.objects.get(content_type__app_label="account", codename="manage_users")
        )

        response = client.patch(
            reverse("user_details", kwargs={"id": actor.id}),
            {"email": actor.email, "is_active": True, "group_ids": [sensitive_group.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert sensitive_group not in User.objects.get(pk=actor.pk).groups.all()

    def test_manage_users_holder_cannot_create_a_user_in_the_admin_group(self):
        client, _actor = _api_client_with_permission("manage_users")
        admin_group_id = Group.objects.get(name=ADMIN_GROUP_NAME).id

        response = client.post(
            reverse("user_list"),
            {
                "email": "escalated@example.com",
                "password": "s3cret!",
                "is_active": True,
                "group_ids": [admin_group_id],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not User.objects.filter(email="escalated@example.com").exists()

    def test_admin_group_member_can_still_assign_any_group(self, admin_api_client):
        target = baker.make(User, is_service_account=False)
        sensitive_group = Group.objects.create(name="Sensitive")
        sensitive_group.permissions.add(
            Permission.objects.get(content_type__app_label="account", codename="manage_users")
        )

        response = admin_api_client.patch(
            reverse("user_details", kwargs={"id": target.id}),
            {"email": target.email, "is_active": True, "group_ids": [sensitive_group.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert sensitive_group in User.objects.get(pk=target.pk).groups.all()


@pytest.mark.django_db
class TestAccountView:
    def test_account_returns_is_admin_true_for_group_member(self, admin_api_client):
        response = admin_api_client.get(reverse("account"))
        assert response.data["is_admin"] is True
        assert "is_staff" not in response.data

    def test_account_returns_is_admin_false_for_staff_only_user(self):
        staff_only = baker.make(User, is_staff=True)
        client = APIClient()
        client.force_authenticate(user=staff_only)
        response = client.get(reverse("account"))
        assert response.data["is_admin"] is False
