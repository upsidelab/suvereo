import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from account.authorization import assign_dataset_role
from account.models import User


@pytest.mark.django_db
class TestDataSetAccessListView:
    def test_admin_can_list_access_grants(self, admin_api_client, data_set):
        viewer = baker.make(User)
        assign_dataset_role(viewer, data_set, "viewer")
        marketing = Group.objects.create(name="Marketing")
        assign_dataset_role(marketing, data_set, "editor")

        response = admin_api_client.get(reverse("data_set_access_list", kwargs={"data_set_id": data_set.id}))

        assert response.status_code == status.HTTP_200_OK
        rows = {(row["target_type"], row["target_id"]): row["role"] for row in response.data}
        assert rows[("user", viewer.id)] == "viewer"
        assert rows[("group", marketing.id)] == "editor"

    def test_non_canonical_grant_is_reported_as_none(self, admin_api_client, data_set):
        from guardian.shortcuts import assign_perm

        user = baker.make(User)
        assign_perm("catalog.manage_agents", user, data_set)  # manage_agents without access_dataset

        response = admin_api_client.get(reverse("data_set_access_list", kwargs={"data_set_id": data_set.id}))

        row = next(r for r in response.data if r["target_type"] == "user" and r["target_id"] == user.id)
        assert row["role"] is None

    def test_regular_user_cannot_list_access_grants(self, api_client, data_set):
        response = api_client.get(reverse("data_set_access_list", kwargs={"data_set_id": data_set.id}))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_grant_viewer_role_to_a_user(self, admin_api_client, data_set):
        target = baker.make(User)

        response = admin_api_client.post(
            reverse("data_set_access_list", kwargs={"data_set_id": data_set.id}),
            {"target_type": "user", "target_id": target.id, "role": "viewer"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert target.has_perm("catalog.access_dataset", data_set) is True

    def test_admin_can_grant_editor_role_to_a_group(self, admin_api_client, data_set):
        group = Group.objects.create(name="Marketing")

        response = admin_api_client.post(
            reverse("data_set_access_list", kwargs={"data_set_id": data_set.id}),
            {"target_type": "group", "target_id": group.id, "role": "editor"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        member = baker.make(User)
        member.groups.add(group)
        assert member.has_perm("catalog.manage_agents", data_set) is True

    def test_invalid_role_rejected(self, admin_api_client, data_set):
        target = baker.make(User)

        response = admin_api_client.post(
            reverse("data_set_access_list", kwargs={"data_set_id": data_set.id}),
            {"target_type": "user", "target_id": target.id, "role": "owner"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_group_member_does_not_appear_as_a_phantom_user_row(self, admin_api_client, data_set):
        group = Group.objects.create(name="Marketing")
        assign_dataset_role(group, data_set, "editor")
        member = baker.make(User)
        member.groups.add(group)

        response = admin_api_client.get(reverse("data_set_access_list", kwargs={"data_set_id": data_set.id}))

        user_rows = [row for row in response.data if row["target_type"] == "user" and row["target_id"] == member.id]
        assert user_rows == []
        group_rows = [row for row in response.data if row["target_type"] == "group" and row["target_id"] == group.id]
        assert len(group_rows) == 1

    def test_editor_cannot_manage_access(self, data_set):
        user = baker.make(User)
        assign_dataset_role(user, data_set, "editor")
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(reverse("data_set_access_list", kwargs={"data_set_id": data_set.id}))

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_downgrading_role_actually_removes_the_higher_roles_permissions(self, admin_api_client, data_set):
        target = baker.make(User)
        assign_dataset_role(target, data_set, "editor")

        response = admin_api_client.post(
            reverse("data_set_access_list", kwargs={"data_set_id": data_set.id}),
            {"target_type": "user", "target_id": target.id, "role": "viewer"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert target.has_perm("catalog.access_dataset", data_set) is True
        assert target.has_perm("catalog.manage_agents", data_set) is False


@pytest.mark.django_db
class TestDataSetAccessDetailView:
    def test_admin_can_revoke_a_users_access(self, admin_api_client, data_set):
        target = baker.make(User)
        assign_dataset_role(target, data_set, "editor")

        response = admin_api_client.delete(
            reverse(
                "data_set_access_detail",
                kwargs={"data_set_id": data_set.id, "target_type": "user", "target_id": target.id},
            )
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert target.has_perm("catalog.access_dataset", data_set) is False
        assert target.has_perm("catalog.manage_agents", data_set) is False

    def test_revoking_a_non_canonical_grant_clears_everything(self, admin_api_client, data_set):
        from guardian.shortcuts import assign_perm

        target = baker.make(User)
        assign_perm("catalog.manage_agents", target, data_set)  # non-canonical: no access_dataset

        response = admin_api_client.delete(
            reverse(
                "data_set_access_detail",
                kwargs={"data_set_id": data_set.id, "target_type": "user", "target_id": target.id},
            )
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert target.has_perm("catalog.manage_agents", data_set) is False

    def test_regular_user_cannot_revoke_access(self, api_client, data_set):
        target = baker.make(User)
        assign_dataset_role(target, data_set, "viewer")

        response = api_client.delete(
            reverse(
                "data_set_access_detail",
                kwargs={"data_set_id": data_set.id, "target_type": "user", "target_id": target.id},
            )
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_invalid_target_type_returns_400(self, admin_api_client, data_set):
        response = admin_api_client.delete(
            reverse(
                "data_set_access_detail",
                kwargs={"data_set_id": data_set.id, "target_type": "bogus", "target_id": 1},
            )
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
