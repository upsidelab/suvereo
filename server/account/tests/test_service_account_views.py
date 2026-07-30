import pytest
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
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
class TestServiceAccountViews:
    def test_regular_user_cannot_list_service_accounts(self, api_client):
        response = api_client.get(reverse("service_account_list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_group_member_can_list_service_accounts(self, admin_api_client):
        response = admin_api_client.get(reverse("service_account_list"))
        assert response.status_code == status.HTTP_200_OK

    def test_create_with_admin_group_id_adds_group_membership(self, admin_api_client):
        admin_group_id = Group.objects.get(name=ADMIN_GROUP_NAME).id
        payload = {"name": "shop-bot", "is_active": True, "group_ids": [admin_group_id], "data_set_ids": []}
        response = admin_api_client.post(reverse("service_account_list"), payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        account = User.objects.get(id=response.data["id"])
        assert account.is_service_account is True
        assert is_application_admin(account) is True
        assert account.is_staff is False

    def test_create_with_no_groups(self, admin_api_client):
        payload = {"name": "scoped-bot", "is_active": True, "group_ids": [], "data_set_ids": []}
        response = admin_api_client.post(reverse("service_account_list"), payload, format="json")
        account = User.objects.get(id=response.data["id"])
        assert is_application_admin(account) is False

    def test_update_toggles_admin_group_membership(self, admin_api_client):
        admin_group_id = Group.objects.get(name=ADMIN_GROUP_NAME).id
        payload = {"name": "toggle-bot", "is_active": True, "group_ids": [admin_group_id], "data_set_ids": []}
        created = admin_api_client.post(reverse("service_account_list"), payload, format="json")
        account_id = created.data["id"]

        response = admin_api_client.patch(
            f"/api/service_accounts/{account_id}",
            {"name": "toggle-bot", "is_active": True, "group_ids": [], "data_set_ids": []},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert is_application_admin(User.objects.get(id=account_id)) is False

    def test_list_exposes_is_admin_and_group_ids(self, admin_api_client):
        admin_group_id = Group.objects.get(name=ADMIN_GROUP_NAME).id
        payload = {"name": "listed-bot", "is_active": True, "group_ids": [admin_group_id], "data_set_ids": []}
        admin_api_client.post(reverse("service_account_list"), payload, format="json")
        response = admin_api_client.get(reverse("service_account_list"))
        items = {item["email"]: item for item in response.data["results"]}
        listed = next(v for k, v in items.items() if k.startswith("listed-bot@"))
        assert listed["is_admin"] is True
        assert listed["group_ids"] == [admin_group_id]
        assert "is_staff" not in listed

    def test_patch_omitting_group_ids_preserves_membership(self, admin_api_client):
        admin_group_id = Group.objects.get(name=ADMIN_GROUP_NAME).id
        payload = {"name": "sticky-bot", "is_active": True, "group_ids": [admin_group_id], "data_set_ids": []}
        created = admin_api_client.post(reverse("service_account_list"), payload, format="json")
        account_id = created.data["id"]

        response = admin_api_client.patch(
            f"/api/service_accounts/{account_id}",
            {"name": "sticky-bot", "is_active": True, "data_set_ids": []},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert is_application_admin(User.objects.get(id=account_id)) is True

    def test_patch_response_exposes_is_admin_and_group_ids(self, admin_api_client):
        admin_group_id = Group.objects.get(name=ADMIN_GROUP_NAME).id
        payload = {"name": "reported-bot", "is_active": True, "group_ids": [admin_group_id], "data_set_ids": []}
        created = admin_api_client.post(reverse("service_account_list"), payload, format="json")
        account_id = created.data["id"]

        response = admin_api_client.patch(
            f"/api/service_accounts/{account_id}",
            {"name": "reported-bot", "is_active": True, "group_ids": [], "data_set_ids": []},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_admin"] is False
        assert response.data["group_ids"] == []
        assert response.data["id"] == account_id


@pytest.mark.django_db
class TestGroupIdsPrivilegeEscalationGuard:
    """Regression tests: `manage_service_accounts` is a delegable permission, so holding it
    must never be enough to grant a service account Admin-equivalent group membership (the
    Admin group itself, or any group that grants `manage_users`/`manage_service_accounts`) —
    only literal Admin-group members may do that.
    """

    def test_manage_service_accounts_holder_cannot_create_a_service_account_in_admin_group(self):
        client, _actor = _api_client_with_permission("manage_service_accounts")
        admin_group_id = Group.objects.get(name=ADMIN_GROUP_NAME).id

        response = client.post(
            reverse("service_account_list"),
            {"name": "escalation-bot", "is_active": True, "group_ids": [admin_group_id], "data_set_ids": []},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not User.objects.filter(email__startswith="escalation-bot@").exists()

    def test_manage_service_accounts_holder_cannot_patch_a_service_account_into_admin_group(self):
        client, _actor = _api_client_with_permission("manage_service_accounts")
        account = baker.make(User, is_service_account=True)
        admin_group_id = Group.objects.get(name=ADMIN_GROUP_NAME).id

        response = client.patch(
            f"/api/service_accounts/{account.id}",
            {"name": "target-bot", "is_active": True, "group_ids": [admin_group_id], "data_set_ids": []},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert is_application_admin(User.objects.get(pk=account.pk)) is False

    def test_manage_service_accounts_holder_cannot_assign_a_group_that_grants_manage_service_accounts(self):
        client, _actor = _api_client_with_permission("manage_service_accounts")
        sensitive_group = Group.objects.create(name="SA Managers")
        sensitive_group.permissions.add(
            Permission.objects.get(content_type__app_label="account", codename="manage_service_accounts")
        )

        response = client.post(
            reverse("service_account_list"),
            {"name": "sneaky-bot", "is_active": True, "group_ids": [sensitive_group.id], "data_set_ids": []},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not User.objects.filter(email__startswith="sneaky-bot@").exists()

    def test_admin_group_member_can_still_assign_any_group(self, admin_api_client):
        sensitive_group = Group.objects.create(name="SA Managers")
        sensitive_group.permissions.add(
            Permission.objects.get(content_type__app_label="account", codename="manage_service_accounts")
        )

        response = admin_api_client.post(
            reverse("service_account_list"),
            {"name": "trusted-bot", "is_active": True, "group_ids": [sensitive_group.id], "data_set_ids": []},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        account = User.objects.get(id=response.data["id"])
        assert sensitive_group in account.groups.all()


@pytest.mark.django_db
class TestCreateAdminServiceAccountCommand:
    def test_command_creates_admin_group_member(self, capsys):
        call_command("createadminserviceaccount", "--name", "cli-bot")
        account = User.objects.get(email__startswith="cli-bot@")
        assert account.is_service_account is True
        assert is_application_admin(account) is True
        assert "Service Account token:" in capsys.readouterr().out
