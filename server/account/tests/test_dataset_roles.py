import pytest
from django.contrib.auth.models import Group
from guardian.shortcuts import get_perms
from model_bakery import baker

from account.authorization import (
    DATASET_PERMISSION_CODENAMES,
    PERM_ACCESS_DATASET,
    PERM_MANAGE_AGENTS,
    assign_dataset_role,
    count_datasets_using_role,
    has_dataset_perm,
    remove_all_dataset_grants,
    remove_dataset_role,
)
from account.models import DatasetRole, User
from catalog.models import DataSet


@pytest.mark.django_db
class TestDatasetRoleCatalog:
    def test_seeded_roles_have_expected_permissions_and_are_system(self):
        viewer = DatasetRole.objects.get(name="viewer")
        editor = DatasetRole.objects.get(name="editor")
        assert {p.codename for p in viewer.permissions.all()} == {"access_dataset"}
        assert {p.codename for p in editor.permissions.all()} == {"access_dataset", "manage_agents"}
        assert viewer.is_system is True
        assert editor.is_system is True

    def test_dataset_permission_codenames_constant(self):
        assert DATASET_PERMISSION_CODENAMES == [PERM_ACCESS_DATASET, PERM_MANAGE_AGENTS]


@pytest.mark.django_db
class TestAssignAndRemoveDatasetRole:
    def test_assign_viewer_to_user_grants_only_access_dataset(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)

        assign_dataset_role(user, dataset, "viewer")

        assert set(get_perms(user, dataset)) == {"access_dataset"}

    def test_assign_editor_to_user_grants_both_permissions(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)

        assign_dataset_role(user, dataset, "editor")

        assert set(get_perms(user, dataset)) == {"access_dataset", "manage_agents"}

    def test_assign_editor_to_group_grants_members_the_permissions(self):
        group = Group.objects.create(name="Marketing")
        member = baker.make(User)
        member.groups.add(group)
        dataset = baker.make(DataSet)

        assign_dataset_role(group, dataset, "editor")

        assert member.has_perm(PERM_MANAGE_AGENTS, dataset) is True

    def test_remove_dataset_role_revokes_the_whole_bundle(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)
        assign_dataset_role(user, dataset, "editor")

        remove_dataset_role(user, dataset, "editor")

        assert get_perms(user, dataset) == []

    def test_remove_all_dataset_grants_clears_a_non_canonical_state(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)
        assign_dataset_role(user, dataset, "editor")

        remove_all_dataset_grants(user, dataset)

        assert get_perms(user, dataset) == []

    def test_assigning_an_unknown_role_name_raises(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)

        with pytest.raises(DatasetRole.DoesNotExist):
            assign_dataset_role(user, dataset, "owner")

    def test_a_custom_role_composed_from_existing_permissions_can_be_assigned(self):
        custom_role = DatasetRole.objects.create(name="viewer-only-custom")
        custom_role.permissions.set(DatasetRole.objects.get(name="viewer").permissions.all())
        user = baker.make(User)
        dataset = baker.make(DataSet)

        assign_dataset_role(user, dataset, "viewer-only-custom")

        assert set(get_perms(user, dataset)) == {"access_dataset"}


@pytest.mark.django_db
class TestCountDatasetsUsingRole:
    def test_zero_when_unused(self):
        assert count_datasets_using_role("viewer") == 0

    def test_counts_a_user_grant_matching_the_role_exactly(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)
        assign_dataset_role(user, dataset, "editor")

        assert count_datasets_using_role("editor") == 1
        assert count_datasets_using_role("viewer") == 0

    def test_counts_a_group_grant_matching_the_role_exactly(self):
        group = Group.objects.create(name="Marketing")
        dataset = baker.make(DataSet)
        assign_dataset_role(group, dataset, "viewer")

        assert count_datasets_using_role("viewer") == 1


@pytest.mark.django_db
class TestHasDatasetPerm:
    def test_global_grant_passes_for_any_dataset(self):
        user = baker.make(User)
        user.user_permissions.add(_permission(PERM_MANAGE_AGENTS))
        dataset = baker.make(DataSet)
        user = User.objects.get(pk=user.pk)  # fresh instance: has_perm caches per object

        assert has_dataset_perm(user, PERM_MANAGE_AGENTS, dataset) is True

    def test_per_dataset_grant_passes_only_for_that_dataset(self):
        user = baker.make(User)
        dataset_a = baker.make(DataSet)
        dataset_b = baker.make(DataSet)
        assign_dataset_role(user, dataset_a, "editor")

        assert has_dataset_perm(user, PERM_MANAGE_AGENTS, dataset_a) is True
        assert has_dataset_perm(user, PERM_MANAGE_AGENTS, dataset_b) is False

    def test_raw_has_perm_alone_would_incorrectly_deny_a_per_dataset_editor(self):
        """Demonstrates exactly the regression has_dataset_perm exists to prevent."""
        user = baker.make(User)
        dataset = baker.make(DataSet)
        assign_dataset_role(user, dataset, "editor")

        assert user.has_perm(PERM_MANAGE_AGENTS) is False
        assert has_dataset_perm(user, PERM_MANAGE_AGENTS, dataset) is True

    def test_neither_grant_denies(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)

        assert has_dataset_perm(user, PERM_MANAGE_AGENTS, dataset) is False


def _permission(codename: str):
    from django.contrib.auth.models import Permission

    app_label, code = codename.split(".")
    return Permission.objects.get(content_type__app_label=app_label, codename=code)
