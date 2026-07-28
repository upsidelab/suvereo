import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import assign_dataset_role, set_application_admin
from account.models import User
from catalog.models import DataSet


@pytest.mark.django_db
class TestHasDatasetAccess:
    def test_admin_group_member_has_access_to_unassigned_dataset(self, data_set):
        user = baker.make(User)
        set_application_admin(user, True)
        user = User.objects.get(pk=user.pk)  # fresh instance: has_perm caches per object
        assert user.has_dataset_access(data_set) is True

    def test_staff_only_user_has_no_access_to_unassigned_dataset(self, data_set):
        user = baker.make(User, is_staff=True)
        assert user.has_dataset_access(data_set) is False

    def test_viewer_has_access(self, data_set):
        user = baker.make(User)
        assign_dataset_role(user, data_set, "viewer")
        assert user.has_dataset_access(data_set) is True

    def test_editor_has_access(self, data_set):
        user = baker.make(User)
        assign_dataset_role(user, data_set, "editor")
        assert user.has_dataset_access(data_set) is True

    def test_unassigned_user_has_no_access(self, data_set):
        user = baker.make(User)
        assert user.has_dataset_access(data_set) is False

    def test_group_member_has_access_via_group_grant(self, data_set):
        from django.contrib.auth.models import Group

        group = Group.objects.create(name="Marketing")
        assign_dataset_role(group, data_set, "viewer")
        user = baker.make(User)
        user.groups.add(group)
        assert user.has_dataset_access(data_set) is True


@pytest.mark.django_db
class TestDataSetListView:
    def test_admin_sees_all_datasets(self, admin_api_client):
        baker.make(DataSet, _quantity=2)
        response = admin_api_client.get(reverse("data_set_list"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

    def test_regular_user_sees_only_assigned_datasets(self, api_client, user):
        assigned = baker.make(DataSet)
        assign_dataset_role(user, assigned, "viewer")
        baker.make(DataSet)
        response = api_client.get(reverse("data_set_list"))
        assert response.data["count"] == 1

    def test_group_member_sees_dataset_granted_to_their_group(self, api_client, user):
        from django.contrib.auth.models import Group

        assigned = baker.make(DataSet)
        group = Group.objects.create(name="Marketing")
        assign_dataset_role(group, assigned, "viewer")
        user.groups.add(group)
        baker.make(DataSet)
        response = api_client.get(reverse("data_set_list"))
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == assigned.id
        assert response.data["results"][0]["id"] == assigned.id

    def test_creator_can_see_the_dataset_they_created(self, api_client, user):
        response = api_client.post(reverse("data_set_list"), {"name": "nope", "preconfigure_agents": False}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN  # regular user still can't create

    def test_regular_user_cannot_create_dataset(self, api_client):
        response = api_client.post(
            reverse("data_set_list"), {"name": "nope", "preconfigure_agents": False}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_creating_a_dataset_becomes_its_editor(self, admin_api_client, admin_user):
        response = admin_api_client.post(
            reverse("data_set_list"), {"name": "new one", "preconfigure_agents": False}, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        dataset = DataSet.objects.get(id=response.data["id"])
        assert admin_user.has_perm("catalog.manage_agents", dataset) is True


@pytest.mark.django_db
class TestAdminOnlyCatalogViews:
    @pytest.mark.parametrize(
        "url_name,url_kwargs",
        [
            ("data_set_detail", {"data_set_id": None}),
            ("config", {}),
        ],
    )
    def test_regular_user_gets_403(self, api_client, data_set, url_name, url_kwargs):
        kwargs = {k: data_set.id for k in url_kwargs}
        response = api_client.get(reverse(url_name, kwargs=kwargs))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_group_member_reads_dataset_detail(self, admin_api_client, data_set):
        response = admin_api_client.get(reverse("data_set_detail", kwargs={"data_set_id": data_set.id}))
        assert response.status_code == status.HTTP_200_OK

    def test_staff_only_user_gets_403_on_config(self):
        staff_only = baker.make(User, is_staff=True)
        client = APIClient()
        client.force_authenticate(user=staff_only)
        response = client.get(reverse("config"))
        assert response.status_code == status.HTTP_403_FORBIDDEN
