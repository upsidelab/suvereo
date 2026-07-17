import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import set_application_admin
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

    def test_assigned_user_has_access(self, data_set):
        user = baker.make(User)
        data_set.users.add(user)
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
        assigned.users.add(user)
        baker.make(DataSet)
        response = api_client.get(reverse("data_set_list"))
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == assigned.id

    def test_regular_user_cannot_create_dataset(self, api_client):
        response = api_client.post(
            reverse("data_set_list"), {"name": "nope", "preconfigure_agents": False}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAdminOnlyCatalogViews:
    @pytest.mark.parametrize(
        "url_name,url_kwargs",
        [
            ("data_set_detail", {"data_set_id": None}),
            ("data_set_user_list", {"data_set_id": None}),
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
