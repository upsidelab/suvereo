import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status


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
