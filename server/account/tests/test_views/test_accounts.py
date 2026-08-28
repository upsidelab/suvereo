import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework import status

from account.authorization import PERMISSIONS, PUBLIC_CODES, permission_label
from account.tests.helpers import assign_role, grant, join_group, make_group, make_role
from account.tests.public_permission_codes_contract import GROUP_ASSIGN, GROUP_VIEW, USER_VIEW

pytestmark = pytest.mark.django_db

# The prefixes an admin's raw `get_all_permissions()` is full of, none of which this application
# ever checks. Before the public vocabulary they were all published to the frontend verbatim.
FRAMEWORK_PREFIXES = ("admin.", "auth.", "authtoken.", "contenttypes.", "sessions.")


@pytest.fixture
def url():
    return reverse("account")


@pytest.fixture
def catalog(admin_api_client):
    """Every code the permission catalog offers under the global scope."""
    response = admin_api_client.get(reverse("permission_list"), {"scope": "global"})
    return {option["code"] for entity in response.data for option in entity["permissions"]}


def test_an_admin_is_reported_as_holding_exactly_the_global_catalog(admin_api_client, url, catalog):
    response = admin_api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert set(response.data["permissions"]) == catalog


def test_an_admin_is_not_told_about_framework_or_plugin_permissions(admin_api_client, url):
    """A superuser's `get_all_permissions()` returns every row in `auth_permission`, most of them
    belonging to Django's own models and to installed plugins. Publishing those told the frontend
    about tables the application never gates on."""
    response = admin_api_client.get(url)

    assert not any(code.startswith(FRAMEWORK_PREFIXES) for code in response.data["permissions"])
    assert len(response.data["permissions"]) < Permission.objects.count()


def test_permissions_is_empty_for_a_user_holding_nothing(api_client, url):
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["permissions"] == []


def test_permissions_lists_a_directly_granted_code(api_client, user, url):
    grant(user, PERMISSIONS.USER.VIEW)

    response = api_client.get(url)

    assert response.data["permissions"] == [USER_VIEW]


def test_permissions_folds_in_codes_granted_through_a_group(api_client, user, url):
    join_group(user, make_group("assigners", PERMISSIONS.GROUP.VIEW, PERMISSIONS.GROUP.ASSIGN))

    response = api_client.get(url)

    assert set(response.data["permissions"]) == {GROUP_VIEW, GROUP_ASSIGN}


def test_permissions_excludes_per_dataset_role_grants(api_client, user, url, data_set):
    assign_role(user, data_set, make_role("converser", PERMISSIONS.CONVERSATION.CONVERSE))

    response = api_client.get(url)

    assert response.data["permissions"] == []


def test_a_permission_outside_the_vocabulary_is_dropped_rather_than_crashing(api_client, user, url):
    undeclared = next(
        row for row in Permission.objects.select_related("content_type") if permission_label(row) not in PUBLIC_CODES
    )
    user.user_permissions.add(undeclared)

    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["permissions"] == []
