import pytest
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from account.models import User


@pytest.mark.django_db
class TestGroupListView:
    def test_admin_group_member_can_list_groups(self, admin_api_client):
        Group.objects.create(name="Marketing")
        Group.objects.create(name="Sales")

        response = admin_api_client.get(reverse("group_list"))

        assert response.status_code == status.HTTP_200_OK
        names = {row["name"] for row in response.data}
        assert {"Admin", "Marketing", "Sales"} <= names

    def test_regular_user_cannot_list_groups(self, api_client):
        response = api_client.get(reverse("group_list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_create_a_group_with_permissions(self, admin_api_client):
        manage_users = Permission.objects.get(content_type__app_label="account", codename="manage_users")

        response = admin_api_client.post(
            reverse("group_list"), {"name": "Support", "permission_ids": [manage_users.id]}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        group = Group.objects.get(name="Support")
        assert set(group.permissions.all()) == {manage_users}

    def test_cannot_assign_a_non_global_permission_to_a_group(self, admin_api_client):
        access_dataset = Permission.objects.get(content_type__app_label="catalog", codename="access_dataset")

        response = admin_api_client.post(
            reverse("group_list"), {"name": "Bogus", "permission_ids": [access_dataset.id]}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_regular_user_cannot_create_a_group(self, api_client):
        response = api_client.post(reverse("group_list"), {"name": "Support", "permission_ids": []}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestGroupDetailView:
    def test_admin_can_update_a_groups_permissions(self, admin_api_client):
        group = Group.objects.create(name="Support")
        manage_users = Permission.objects.get(content_type__app_label="account", codename="manage_users")

        response = admin_api_client.patch(
            reverse("group_detail", kwargs={"group_id": group.id}),
            {"name": "Support", "permission_ids": [manage_users.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        group.refresh_from_db()
        assert set(group.permissions.all()) == {manage_users}

    def test_admin_group_is_reported_as_system(self, admin_api_client):
        admin_group = Group.objects.get(name="Admin")
        response = admin_api_client.get(reverse("group_detail", kwargs={"group_id": admin_group.id}))
        assert response.data["is_system"] is True

    def test_non_admin_group_is_not_system(self, admin_api_client):
        group = Group.objects.create(name="Support")
        response = admin_api_client.get(reverse("group_detail", kwargs={"group_id": group.id}))
        assert response.data["is_system"] is False

    def test_admin_can_delete_a_non_system_group(self, admin_api_client):
        group = Group.objects.create(name="Support")
        response = admin_api_client.delete(reverse("group_detail", kwargs={"group_id": group.id}))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Group.objects.filter(pk=group.pk).exists()

    def test_admin_group_cannot_be_deleted(self, admin_api_client):
        admin_group = Group.objects.get(name="Admin")
        response = admin_api_client.delete(reverse("group_detail", kwargs={"group_id": admin_group.id}))
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Group.objects.filter(pk=admin_group.pk).exists()

    def test_regular_user_cannot_delete_a_group(self, api_client):
        group = Group.objects.create(name="Support")
        response = api_client.delete(reverse("group_detail", kwargs={"group_id": group.id}))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_group_cannot_be_renamed(self, admin_api_client):
        admin_group = Group.objects.get(name="Admin")

        response = admin_api_client.patch(
            reverse("group_detail", kwargs={"group_id": admin_group.id}),
            {"name": "Superusers", "permission_ids": []},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        admin_group.refresh_from_db()
        assert admin_group.name == "Admin"

    def test_admin_groups_permissions_can_still_be_updated_without_renaming(self, admin_api_client):
        admin_group = Group.objects.get(name="Admin")
        manage_users = Permission.objects.get(content_type__app_label="account", codename="manage_users")

        response = admin_api_client.patch(
            reverse("group_detail", kwargs={"group_id": admin_group.id}),
            {"name": "Admin", "permission_ids": [manage_users.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        admin_group.refresh_from_db()
        assert admin_group.name == "Admin"
        assert set(admin_group.permissions.all()) == {manage_users}


@pytest.mark.django_db
class TestGroupMembersView:
    def test_admin_can_list_members(self, admin_api_client):
        group = Group.objects.create(name="Support")
        member = baker.make(User, email="member@example.com")
        member.groups.add(group)

        response = admin_api_client.get(reverse("group_members", kwargs={"group_id": group.id}))

        assert response.status_code == status.HTTP_200_OK
        assert [row["email"] for row in response.data] == ["member@example.com"]

    def test_admin_can_add_a_member(self, admin_api_client):
        group = Group.objects.create(name="Support")
        user = baker.make(User)

        response = admin_api_client.post(
            reverse("group_members", kwargs={"group_id": group.id}), {"user_id": user.id}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert group in user.groups.all()

    def test_admin_can_remove_a_member(self, admin_api_client):
        group = Group.objects.create(name="Support")
        user = baker.make(User)
        user.groups.add(group)

        response = admin_api_client.delete(
            reverse("group_member_detail", kwargs={"group_id": group.id, "user_id": user.id})
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert group not in user.groups.all()

    def test_regular_user_cannot_list_members(self, api_client):
        group = Group.objects.create(name="Support")
        response = api_client.get(reverse("group_members", kwargs={"group_id": group.id}))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_add_member_with_non_numeric_user_id_returns_400(self, admin_api_client):
        group = Group.objects.create(name="Support")

        response = admin_api_client.post(
            reverse("group_members", kwargs={"group_id": group.id}), {"user_id": "not-a-number"}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
