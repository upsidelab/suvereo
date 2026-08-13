import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from account.authorization import PERMISSIONS
from account.models import DatasetRole, DatasetUserRoleAssignment
from catalog.models import DataSet

pytestmark = pytest.mark.django_db


def _permission(codename: str) -> Permission:
    app_label, name = codename.split(".")
    return Permission.objects.get(codename=name, content_type__app_label=app_label)


@pytest.fixture
def url():
    return reverse("account")


def test_permissions_is_empty_for_a_user_holding_nothing(api_client, url):
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["permissions"] == []


def test_permissions_lists_directly_granted_codenames(api_client, user, url):
    user.user_permissions.add(_permission(PERMISSIONS.USER.VIEW))

    response = api_client.get(url)

    assert response.data["permissions"] == [PERMISSIONS.USER.VIEW]


def test_permissions_includes_codenames_granted_through_a_group(api_client, user, url):
    group = baker.make("auth.Group")
    group.permissions.add(_permission(PERMISSIONS.SERVICE_ACCOUNT.VIEW))
    user.groups.add(group)

    response = api_client.get(url)

    assert PERMISSIONS.SERVICE_ACCOUNT.VIEW in response.data["permissions"]


def test_permissions_excludes_per_dataset_role_grants(api_client, user, url):
    role = baker.make(DatasetRole)
    role.permissions.add(_permission(PERMISSIONS.AGENT.VIEW))
    baker.make(DatasetUserRoleAssignment, user=user, dataset=baker.make(DataSet), role=role)

    response = api_client.get(url)

    assert response.data["permissions"] == []


def test_admin_holds_every_permission(admin_api_client, url):
    response = admin_api_client.get(url)

    assert PERMISSIONS.USER.VIEW in response.data["permissions"]
    assert PERMISSIONS.SERVICE_ACCOUNT.ADD in response.data["permissions"]
    assert len(response.data["permissions"]) == Permission.objects.count()
