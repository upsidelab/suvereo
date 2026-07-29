import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status

from account.authorization import ADMIN_GROUP_NAME, is_application_admin
from account.models import User


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
class TestCreateAdminServiceAccountCommand:
    def test_command_creates_admin_group_member(self, capsys):
        call_command("createadminserviceaccount", "--name", "cli-bot")
        account = User.objects.get(email__startswith="cli-bot@")
        assert account.is_service_account is True
        assert is_application_admin(account) is True
        assert "Service Account token:" in capsys.readouterr().out
