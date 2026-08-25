import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from model_bakery import baker
from rest_framework import serializers, status

from account.authorization import PERMISSIONS
from account.models import DatasetGlobalRoleAssignment, DatasetRole, DatasetUserRoleAssignment, GlobalRole
from agent.models import Agent
from catalog.entities.registry import EntityRegistration, entity_registry
from catalog.models import DataSet

pytestmark = pytest.mark.django_db


class _AgentTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ["id", "name"]


@pytest.fixture(autouse=True)
def fake_entity_registration(monkeypatch):
    """Stand in for a real `CATALOG_ENTITY_PLUGINS`-registered entity — the permission
    check under test lives in `get_queryset()`, before any real entity plugin matters."""
    registration = EntityRegistration(
        slug="agents",
        label="Agents",
        model=Agent,
        fields=[],
        serializer=_AgentTestSerializer,
    )
    monkeypatch.setattr(entity_registry, "get", lambda slug: registration if slug == "agents" else None)
    return registration


def _permission(codename: str) -> Permission:
    app_label, name = codename.split(".")
    return Permission.objects.get(codename=name, content_type__app_label=app_label)


def _url(data_set, slug="agents"):
    return reverse("entity-records", kwargs={"data_set_id": data_set.id, "slug": slug})


class TestEntityListView:
    def test_outsider_with_no_dataset_at_all_is_denied(self, api_client):
        response = api_client.get(reverse("entity-list"))

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_dataset_member_is_allowed(self, api_client, user, data_set):
        role = baker.make(DatasetRole)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=data_set, role=role)

        response = api_client.get(reverse("entity-list"))

        assert response.status_code == status.HTTP_200_OK

    def test_global_view_dataset_holder_is_allowed(self, api_client, user):
        user.user_permissions.add(_permission(PERMISSIONS.DATASET.VIEW))

        response = api_client.get(reverse("entity-list"))

        assert response.status_code == status.HTTP_200_OK

    def test_admin_is_allowed(self, admin_api_client):
        response = admin_api_client.get(reverse("entity-list"))

        assert response.status_code == status.HTTP_200_OK


class TestEntityRecordsView:
    def test_outsider_is_denied(self, api_client, data_set):
        # Obscured as 404, not 403 - a non-member shouldn't be able to tell this dataset
        # apart from one that doesn't exist.
        response = api_client.get(_url(data_set))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_dataset_returns_404(self, api_client):
        response = api_client.get(reverse("entity-records", kwargs={"data_set_id": 9999, "slug": "agents"}))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_direct_role_member_is_allowed(self, api_client, user, data_set):
        role = baker.make(DatasetRole)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=data_set, role=role)
        baker.make(Agent, dataset=data_set)

        response = api_client.get(_url(data_set))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_global_role_member_is_allowed(self, api_client, user, data_set):
        global_role = baker.make(GlobalRole)
        global_role.members.add(user)
        role = baker.make(DatasetRole)
        baker.make(DatasetGlobalRoleAssignment, global_role=global_role, dataset=data_set, role=role)

        response = api_client.get(_url(data_set))

        assert response.status_code == status.HTTP_200_OK

    def test_global_view_dataset_holder_is_allowed(self, api_client, user, data_set):
        user.user_permissions.add(_permission(PERMISSIONS.DATASET.VIEW))

        response = api_client.get(_url(data_set))

        assert response.status_code == status.HTTP_200_OK

    def test_admin_is_allowed(self, admin_api_client, data_set):
        response = admin_api_client.get(_url(data_set))

        assert response.status_code == status.HTTP_200_OK

    def test_unknown_entity_slug_is_404_even_for_admin(self, admin_api_client, data_set):
        response = admin_api_client.get(_url(data_set, slug="unknown"))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_records_are_scoped_to_the_requested_dataset(self, admin_api_client, data_set):
        other_dataset = baker.make(DataSet)
        baker.make(Agent, dataset=data_set)
        baker.make(Agent, dataset=other_dataset)

        response = admin_api_client.get(_url(data_set))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
