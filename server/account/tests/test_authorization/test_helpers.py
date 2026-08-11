import pytest
from django.contrib.auth.models import Group, Permission
from model_bakery import baker

from account.authorization import PERMISSIONS
from account.authorization.helpers import datasets_visible_to, has_dataset_perm, is_dataset_member
from account.models import DatasetGroupRoleAssignment, DatasetRole, DatasetUserRoleAssignment, User
from catalog.models import DataSet

pytestmark = pytest.mark.django_db


def _permission(codename: str) -> Permission:
    app_label, name = codename.split(".")
    return Permission.objects.get(codename=name, content_type__app_label=app_label)


class TestIsDatasetMember:
    def test_superuser_is_member_of_any_dataset(self):
        user = baker.make(User, is_superuser=True)
        dataset = baker.make(DataSet)

        assert is_dataset_member(user, dataset) is True

    def test_global_view_dataset_holder_is_member_of_any_dataset(self):
        user = baker.make(User)
        user.user_permissions.add(_permission(PERMISSIONS.DATASET.VIEW))
        dataset = baker.make(DataSet)

        assert is_dataset_member(user, dataset) is True

    def test_user_with_direct_role_assignment_is_member(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)

        assert is_dataset_member(user, dataset) is True

    def test_user_with_group_role_assignment_is_member(self):
        user = baker.make(User)
        group = baker.make(Group)
        user.groups.add(group)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetGroupRoleAssignment, group=group, dataset=dataset, role=role)

        assert is_dataset_member(user, dataset) is True

    def test_plain_user_is_not_member(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)

        assert is_dataset_member(user, dataset) is False

    def test_role_assignment_on_different_dataset_does_not_grant_membership(self):
        user = baker.make(User)
        own_dataset = baker.make(DataSet)
        other_dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=own_dataset, role=role)

        assert is_dataset_member(user, other_dataset) is False


class TestDatasetsVisibleTo:
    def test_superuser_sees_all_datasets(self):
        user = baker.make(User, is_superuser=True)
        baker.make(DataSet, _quantity=3)

        assert datasets_visible_to(user).count() == 3

    def test_global_view_dataset_holder_sees_all_datasets(self):
        user = baker.make(User)
        user.user_permissions.add(_permission(PERMISSIONS.DATASET.VIEW))
        baker.make(DataSet, _quantity=2)

        assert datasets_visible_to(user).count() == 2

    def test_user_sees_only_directly_assigned_datasets(self):
        user = baker.make(User)
        visible = baker.make(DataSet)
        baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=visible, role=role)

        assert list(datasets_visible_to(user)) == [visible]

    def test_user_sees_only_group_assigned_datasets(self):
        user = baker.make(User)
        group = baker.make(Group)
        user.groups.add(group)
        visible = baker.make(DataSet)
        baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetGroupRoleAssignment, group=group, dataset=visible, role=role)

        assert list(datasets_visible_to(user)) == [visible]

    def test_sees_union_of_direct_and_group_assignments_without_duplicates(self):
        user = baker.make(User)
        group = baker.make(Group)
        user.groups.add(group)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)
        baker.make(DatasetGroupRoleAssignment, group=group, dataset=dataset, role=role)

        assert list(datasets_visible_to(user)) == [dataset]

    def test_plain_user_sees_no_datasets(self):
        user = baker.make(User)
        baker.make(DataSet)

        assert datasets_visible_to(user).count() == 0


class TestHasDatasetPerm:
    CODENAME = PERMISSIONS.AGENT.VIEW

    def test_superuser_has_any_dataset_perm(self):
        user = baker.make(User, is_superuser=True)
        dataset = baker.make(DataSet)

        assert has_dataset_perm(user, self.CODENAME, dataset) is True

    def test_global_permission_holder_has_dataset_perm_anywhere(self):
        user = baker.make(User)
        user.user_permissions.add(_permission(PERMISSIONS.AGENT.VIEW))
        dataset = baker.make(DataSet)

        assert has_dataset_perm(user, self.CODENAME, dataset) is True

    def test_user_role_assignment_with_matching_permission_grants_access(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        role.permissions.add(_permission(PERMISSIONS.AGENT.VIEW))
        baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)

        assert has_dataset_perm(user, self.CODENAME, dataset) is True

    def test_group_role_assignment_with_matching_permission_grants_access(self):
        user = baker.make(User)
        group = baker.make(Group)
        user.groups.add(group)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        role.permissions.add(_permission(PERMISSIONS.AGENT.VIEW))
        baker.make(DatasetGroupRoleAssignment, group=group, dataset=dataset, role=role)

        assert has_dataset_perm(user, self.CODENAME, dataset) is True

    def test_role_assignment_without_matching_permission_denies_access(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)

        assert has_dataset_perm(user, self.CODENAME, dataset) is False

    def test_role_assignment_on_different_dataset_denies_access(self):
        user = baker.make(User)
        own_dataset = baker.make(DataSet)
        other_dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        role.permissions.add(_permission(PERMISSIONS.AGENT.VIEW))
        baker.make(DatasetUserRoleAssignment, user=user, dataset=own_dataset, role=role)

        assert has_dataset_perm(user, self.CODENAME, other_dataset) is False

    def test_plain_user_denied(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)

        assert has_dataset_perm(user, self.CODENAME, dataset) is False
