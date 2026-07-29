import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from account.authorization import assign_dataset_role
from account.models import DatasetRole, User


@pytest.mark.django_db
class TestDatasetRoleListView:
    def test_admin_can_list_seeded_roles(self, admin_api_client):
        response = admin_api_client.get(reverse("dataset_role_list"))
        assert response.status_code == status.HTTP_200_OK
        names = {row["name"] for row in response.data}
        assert {"viewer", "editor"} <= names

    def test_regular_user_cannot_list(self, api_client):
        response = api_client.get(reverse("dataset_role_list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_create_a_dataset_role(self, admin_api_client):
        access_dataset = Permission.objects.get(content_type__app_label="catalog", codename="access_dataset")

        response = admin_api_client.post(
            reverse("dataset_role_list"), {"name": "read-only", "permission_ids": [access_dataset.id]}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        role = DatasetRole.objects.get(name="read-only")
        assert set(role.permissions.all()) == {access_dataset}
        assert role.is_system is False

    def test_cannot_assign_a_global_permission_to_a_dataset_role(self, admin_api_client):
        manage_users = Permission.objects.get(content_type__app_label="account", codename="manage_users")

        response = admin_api_client.post(
            reverse("dataset_role_list"), {"name": "bogus", "permission_ids": [manage_users.id]}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestDatasetRoleDetailView:
    def test_admin_can_update_permissions(self, admin_api_client):
        access_dataset = Permission.objects.get(content_type__app_label="catalog", codename="access_dataset")
        manage_agents = Permission.objects.get(content_type__app_label="catalog", codename="manage_agents")
        role = DatasetRole.objects.create(name="custom")
        role.permissions.set([access_dataset])

        response = admin_api_client.patch(
            reverse("dataset_role_detail", kwargs={"dataset_role_id": role.id}),
            {"name": "custom", "permission_ids": [access_dataset.id, manage_agents.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        role.refresh_from_db()
        assert set(role.permissions.all()) == {access_dataset, manage_agents}

    def test_admin_can_delete_an_unused_custom_role(self, admin_api_client):
        role = DatasetRole.objects.create(name="custom")

        response = admin_api_client.delete(reverse("dataset_role_detail", kwargs={"dataset_role_id": role.id}))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not DatasetRole.objects.filter(pk=role.pk).exists()

    def test_seeded_viewer_role_cannot_be_deleted(self, admin_api_client):
        viewer = DatasetRole.objects.get(name="viewer")

        response = admin_api_client.delete(reverse("dataset_role_detail", kwargs={"dataset_role_id": viewer.id}))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert DatasetRole.objects.filter(pk=viewer.pk).exists()

    def test_a_role_currently_granted_on_a_dataset_cannot_be_deleted(self, admin_api_client, data_set):
        role = DatasetRole.objects.create(name="custom")
        role.permissions.set(DatasetRole.objects.get(name="viewer").permissions.all())
        user = baker.make(User)
        assign_dataset_role(user, data_set, "custom")

        response = admin_api_client.delete(reverse("dataset_role_detail", kwargs={"dataset_role_id": role.id}))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert DatasetRole.objects.filter(pk=role.pk).exists()

    def test_regular_user_cannot_delete(self, api_client):
        role = DatasetRole.objects.create(name="custom")
        response = api_client.delete(reverse("dataset_role_detail", kwargs={"dataset_role_id": role.id}))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize("system_role_name", ["viewer", "editor"])
    def test_renaming_a_system_role_is_rejected(self, admin_api_client, system_role_name):
        role = DatasetRole.objects.get(name=system_role_name)
        permission_ids = list(role.permissions.values_list("id", flat=True))

        response = admin_api_client.patch(
            reverse("dataset_role_detail", kwargs={"dataset_role_id": role.id}),
            {"name": "renamed-role", "permission_ids": permission_ids},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        role.refresh_from_db()
        assert role.name == system_role_name

    def test_editing_editor_permissions_without_renaming_succeeds(self, admin_api_client):
        editor = DatasetRole.objects.get(name="editor")
        access_dataset = Permission.objects.get(content_type__app_label="catalog", codename="access_dataset")

        response = admin_api_client.patch(
            reverse("dataset_role_detail", kwargs={"dataset_role_id": editor.id}),
            {"name": "editor", "permission_ids": [access_dataset.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        editor.refresh_from_db()
        assert editor.name == "editor"
        assert set(editor.permissions.all()) == {access_dataset}

    def test_renaming_a_non_system_custom_role_succeeds(self, admin_api_client):
        role = DatasetRole.objects.create(name="custom")

        response = admin_api_client.patch(
            reverse("dataset_role_detail", kwargs={"dataset_role_id": role.id}),
            {"name": "renamed-custom", "permission_ids": []},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        role.refresh_from_db()
        assert role.name == "renamed-custom"
