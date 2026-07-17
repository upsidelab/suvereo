import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import is_application_admin, set_application_admin
from account.models import User


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

    def test_listed_users_expose_is_admin(self, admin_api_client, admin_user):
        response = admin_api_client.get(reverse("user_list"))
        by_id = {item["id"]: item for item in response.data["results"]}
        assert by_id[admin_user.id]["is_admin"] is True
        assert "is_staff" not in by_id[admin_user.id]

    def test_create_user_with_is_admin_true_adds_group_membership(self, admin_api_client):
        payload = {"email": "new-admin@example.com", "password": "s3cret!", "is_active": True, "is_admin": True}
        response = admin_api_client.post(reverse("user_list"), payload)
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email="new-admin@example.com")
        assert is_application_admin(user) is True
        assert user.is_staff is False

    def test_create_user_with_is_admin_false(self, admin_api_client):
        payload = {"email": "regular@example.com", "password": "s3cret!", "is_active": True, "is_admin": False}
        admin_api_client.post(reverse("user_list"), payload)
        user = User.objects.get(email="regular@example.com")
        assert is_application_admin(user) is False


@pytest.mark.django_db
class TestUserUpdateView:
    def test_update_toggles_admin_group_membership(self, admin_api_client):
        user = baker.make(User, is_service_account=False)
        url = reverse("user_details", kwargs={"id": user.id})
        payload = {"email": user.email, "is_active": True, "is_admin": True}
        response = admin_api_client.put(url, payload)
        assert response.status_code == status.HTTP_200_OK
        assert is_application_admin(User.objects.get(pk=user.pk)) is True

        payload["is_admin"] = False
        admin_api_client.put(url, payload)
        assert is_application_admin(User.objects.get(pk=user.pk)) is False

    def test_update_does_not_touch_is_staff(self, admin_api_client):
        user = baker.make(User, is_service_account=False, is_staff=False)
        url = reverse("user_details", kwargs={"id": user.id})
        admin_api_client.put(url, {"email": user.email, "is_active": True, "is_admin": True})
        assert User.objects.get(pk=user.pk).is_staff is False


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
