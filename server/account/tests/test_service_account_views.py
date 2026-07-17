import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status

from account.authorization import is_application_admin
from account.models import User


@pytest.mark.django_db
class TestServiceAccountViews:
    def test_regular_user_cannot_list_service_accounts(self, api_client):
        response = api_client.get(reverse("service_account_list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_group_member_can_list_service_accounts(self, admin_api_client):
        response = admin_api_client.get(reverse("service_account_list"))
        assert response.status_code == status.HTTP_200_OK

    def test_create_with_is_admin_true_adds_group_membership(self, admin_api_client):
        payload = {"name": "shop-bot", "is_active": True, "is_admin": True, "data_set_ids": []}
        response = admin_api_client.post(reverse("service_account_list"), payload)
        assert response.status_code == status.HTTP_201_CREATED
        account = User.objects.get(id=response.data["id"])
        assert account.is_service_account is True
        assert is_application_admin(account) is True
        assert account.is_staff is False

    def test_create_with_is_admin_false(self, admin_api_client):
        payload = {"name": "scoped-bot", "is_active": True, "is_admin": False, "data_set_ids": []}
        response = admin_api_client.post(reverse("service_account_list"), payload)
        account = User.objects.get(id=response.data["id"])
        assert is_application_admin(account) is False

    def test_update_toggles_admin_group_membership(self, admin_api_client):
        payload = {"name": "toggle-bot", "is_active": True, "is_admin": True, "data_set_ids": []}
        created = admin_api_client.post(reverse("service_account_list"), payload)
        account_id = created.data["id"]

        payload["is_admin"] = False
        response = admin_api_client.patch(f"/api/service_accounts/{account_id}", payload)
        assert response.status_code == status.HTTP_200_OK
        assert is_application_admin(User.objects.get(id=account_id)) is False

    def test_list_exposes_is_admin(self, admin_api_client):
        payload = {"name": "listed-bot", "is_active": True, "is_admin": True, "data_set_ids": []}
        admin_api_client.post(reverse("service_account_list"), payload)
        response = admin_api_client.get(reverse("service_account_list"))
        items = {item["email"]: item for item in response.data["results"]}
        listed = next(v for k, v in items.items() if k.startswith("listed-bot@"))
        assert listed["is_admin"] is True
        assert "is_staff" not in listed

    def test_patch_omitting_is_admin_preserves_membership(self, admin_api_client):
        payload = {"name": "sticky-bot", "is_active": True, "is_admin": True, "data_set_ids": []}
        created = admin_api_client.post(reverse("service_account_list"), payload)
        account_id = created.data["id"]

        response = admin_api_client.patch(
            f"/api/service_accounts/{account_id}",
            {"name": "sticky-bot", "is_active": True, "data_set_ids": []},
        )
        assert response.status_code == status.HTTP_200_OK
        assert is_application_admin(User.objects.get(id=account_id)) is True


@pytest.mark.django_db
class TestCreateAdminServiceAccountCommand:
    def test_command_creates_admin_group_member(self, capsys):
        call_command("createadminserviceaccount", "--name", "cli-bot")
        account = User.objects.get(email__startswith="cli-bot@")
        assert account.is_service_account is True
        assert is_application_admin(account) is True
        assert "Service Account token:" in capsys.readouterr().out
