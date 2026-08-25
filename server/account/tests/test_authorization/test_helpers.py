import pytest
from django.contrib.auth.models import Permission
from model_bakery import baker

from account.authorization import PERMISSIONS
from account.authorization.helpers import (
    dataset_permission_codes,
    datasets_visible_to,
    datasets_with_permission,
    has_any_dataset_access,
    has_any_permission_on_any_dataset,
    has_dataset_perm,
    is_dataset_member,
)
from account.models import DatasetGlobalRoleAssignment, DatasetRole, DatasetUserRoleAssignment, GlobalRole, User
from account.tests.helpers import grant
from account.tests.public_permission_codes_contract import (
    AGENT_VIEW,
    CONVERSATION_CONVERSE,
    DATASET_SCOPED_CONTRACT,
    DATASET_VIEW,
    INTEGRATION_SYNC,
    INTEGRATION_VIEW,
)
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
        grant(user, PERMISSIONS.DATASET.VIEW)
        dataset = baker.make(DataSet)

        assert is_dataset_member(user, dataset) is True

    def test_user_with_direct_role_assignment_is_member(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)

        assert is_dataset_member(user, dataset) is True

    def test_user_with_global_role_assignment_is_member(self):
        user = baker.make(User)
        global_role = baker.make(GlobalRole)
        global_role.members.add(user)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetGlobalRoleAssignment, global_role=global_role, dataset=dataset, role=role)

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
        grant(user, PERMISSIONS.DATASET.VIEW)
        baker.make(DataSet, _quantity=2)

        assert datasets_visible_to(user).count() == 2

    def test_user_sees_only_directly_assigned_datasets(self):
        user = baker.make(User)
        visible = baker.make(DataSet)
        baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=visible, role=role)

        assert list(datasets_visible_to(user)) == [visible]

    def test_user_sees_only_datasets_assigned_through_a_global_role(self):
        user = baker.make(User)
        global_role = baker.make(GlobalRole)
        global_role.members.add(user)
        visible = baker.make(DataSet)
        baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetGlobalRoleAssignment, global_role=global_role, dataset=visible, role=role)

        assert list(datasets_visible_to(user)) == [visible]

    def test_sees_union_of_direct_and_global_role_assignments_without_duplicates(self):
        user = baker.make(User)
        global_role = baker.make(GlobalRole)
        global_role.members.add(user)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)
        baker.make(DatasetGlobalRoleAssignment, global_role=global_role, dataset=dataset, role=role)

        assert list(datasets_visible_to(user)) == [dataset]

    def test_plain_user_sees_no_datasets(self):
        user = baker.make(User)
        baker.make(DataSet)

        assert datasets_visible_to(user).count() == 0


class TestHasDatasetPerm:
    CODENAME = PERMISSIONS.AGENT.VIEW

    def test_superuser_has_dataset_perm(self):
        user = baker.make(User, is_superuser=True)
        dataset = baker.make(DataSet)

        assert has_dataset_perm(user, self.CODENAME, dataset) is True

    def test_global_permission_holder_has_dataset_perm_anywhere(self):
        user = baker.make(User)
        grant(user, PERMISSIONS.AGENT.VIEW)
        dataset = baker.make(DataSet)

        assert has_dataset_perm(user, self.CODENAME, dataset) is True

    def test_user_role_assignment_with_matching_permission_grants_access(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        role.permissions.add(_permission(PERMISSIONS.AGENT.VIEW))
        baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)

        assert has_dataset_perm(user, self.CODENAME, dataset) is True

    def test_global_role_assignment_with_matching_permission_grants_access(self):
        user = baker.make(User)
        global_role = baker.make(GlobalRole)
        global_role.members.add(user)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        role.permissions.add(_permission(PERMISSIONS.AGENT.VIEW))
        baker.make(DatasetGlobalRoleAssignment, global_role=global_role, dataset=dataset, role=role)

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


class TestDatasetsWithPermission:
    CODENAME = PERMISSIONS.CONVERSATION.VIEW_ALL

    def test_superuser_gets_all_datasets(self):
        user = baker.make(User, is_superuser=True)
        baker.make(DataSet)
        baker.make(DataSet)

        assert datasets_with_permission(user, self.CODENAME).count() == 2

    def test_global_permission_holder_gets_all_datasets(self):
        user = baker.make(User)
        grant(user, PERMISSIONS.CONVERSATION.VIEW_ALL)
        baker.make(DataSet)
        baker.make(DataSet)

        assert datasets_with_permission(user, self.CODENAME).count() == 2

    def test_user_role_assignment_yields_only_that_dataset(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)
        baker.make(DataSet)
        role = baker.make(DatasetRole)
        role.permissions.add(_permission(PERMISSIONS.CONVERSATION.VIEW_ALL))
        baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)

        assert list(datasets_with_permission(user, self.CODENAME)) == [dataset]

    def test_global_role_assignment_yields_only_that_dataset(self):
        user = baker.make(User)
        global_role = baker.make(GlobalRole)
        global_role.members.add(user)
        dataset = baker.make(DataSet)
        baker.make(DataSet)
        role = baker.make(DatasetRole)
        role.permissions.add(_permission(PERMISSIONS.CONVERSATION.VIEW_ALL))
        baker.make(DatasetGlobalRoleAssignment, global_role=global_role, dataset=dataset, role=role)

        assert list(datasets_with_permission(user, self.CODENAME)) == [dataset]

    def test_direct_and_global_role_assignments_are_unioned_without_duplicates(self):
        user = baker.make(User)
        global_role = baker.make(GlobalRole)
        global_role.members.add(user)
        role = baker.make(DatasetRole)
        role.permissions.add(_permission(PERMISSIONS.CONVERSATION.VIEW_ALL))
        direct_dataset = baker.make(DataSet)
        global_role_dataset = baker.make(DataSet)
        shared_dataset = baker.make(DataSet)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=direct_dataset, role=role)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=shared_dataset, role=role)
        baker.make(DatasetGlobalRoleAssignment, global_role=global_role, dataset=global_role_dataset, role=role)
        baker.make(DatasetGlobalRoleAssignment, global_role=global_role, dataset=shared_dataset, role=role)

        result = datasets_with_permission(user, self.CODENAME)

        assert result.count() == 3
        assert set(result) == {direct_dataset, global_role_dataset, shared_dataset}

    def test_role_without_matching_permission_yields_nothing(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)

        assert not datasets_with_permission(user, self.CODENAME).exists()

    def test_plain_user_gets_nothing(self):
        user = baker.make(User)
        baker.make(DataSet)

        assert not datasets_with_permission(user, self.CODENAME).exists()


class TestHasAnyDatasetAccess:
    def test_superuser_has_it_with_no_datasets_at_all(self):
        user = baker.make(User, is_superuser=True)

        assert has_any_dataset_access(user) is True

    def test_global_view_dataset_holder_has_it_with_no_datasets_at_all(self):
        user = baker.make(User)
        grant(user, PERMISSIONS.DATASET.VIEW)

        assert has_any_dataset_access(user) is True

    def test_direct_role_assignment_on_any_dataset_grants_it(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)

        assert has_any_dataset_access(user) is True

    def test_global_role_assignment_on_any_dataset_grants_it(self):
        user = baker.make(User)
        global_role = baker.make(GlobalRole)
        global_role.members.add(user)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetGlobalRoleAssignment, global_role=global_role, dataset=dataset, role=role)

        assert has_any_dataset_access(user) is True

    def test_plain_user_with_no_datasets_denied(self):
        user = baker.make(User)
        baker.make(DataSet)

        assert has_any_dataset_access(user) is False


class TestHasAnyPermissionOnAnyDataset:
    CODENAMES = (PERMISSIONS.AGENT.ADD, PERMISSIONS.AGENT.CHANGE)

    def test_superuser_has_it(self):
        user = baker.make(User, is_superuser=True)

        assert has_any_permission_on_any_dataset(user, *self.CODENAMES) is True

    def test_global_permission_holder_has_it(self):
        user = baker.make(User)
        grant(user, PERMISSIONS.AGENT.ADD)

        assert has_any_permission_on_any_dataset(user, *self.CODENAMES) is True

    def test_role_assignment_on_any_dataset_grants_it(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        role.permissions.add(_permission(PERMISSIONS.AGENT.CHANGE))
        baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)

        assert has_any_permission_on_any_dataset(user, *self.CODENAMES) is True

    def test_global_role_assignment_on_any_dataset_grants_it(self):
        user = baker.make(User)
        global_role = baker.make(GlobalRole)
        global_role.members.add(user)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        role.permissions.add(_permission(PERMISSIONS.AGENT.ADD))
        baker.make(DatasetGlobalRoleAssignment, global_role=global_role, dataset=dataset, role=role)

        assert has_any_permission_on_any_dataset(user, *self.CODENAMES) is True

    def test_role_assignment_without_matching_permission_denies_it(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)

        assert has_any_permission_on_any_dataset(user, *self.CODENAMES) is False

    def test_plain_user_denied(self):
        user = baker.make(User)

        assert has_any_permission_on_any_dataset(user, *self.CODENAMES) is False


class TestDatasetPermissionCodes:
    def test_direct_role_assignment_reports_exactly_its_codes_on_that_dataset(self):
        user = baker.make(User)
        assigned = baker.make(DataSet)
        other = baker.make(DataSet)
        role = baker.make(DatasetRole)
        role.permissions.add(_permission(PERMISSIONS.AGENT.VIEW), _permission(PERMISSIONS.CONVERSATION.CONVERSE))
        baker.make(DatasetUserRoleAssignment, user=user, dataset=assigned, role=role)

        assert dataset_permission_codes(user, assigned) == [AGENT_VIEW, CONVERSATION_CONVERSE]
        assert dataset_permission_codes(user, other) == []

    def test_global_role_assignment_reaches_members(self):
        user = baker.make(User)
        global_role = baker.make(GlobalRole)
        global_role.members.add(user)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        role.permissions.add(_permission(PERMISSIONS.INTEGRATION.VIEW), _permission(PERMISSIONS.INTEGRATION.SYNC))
        baker.make(DatasetGlobalRoleAssignment, global_role=global_role, dataset=dataset, role=role)

        assert dataset_permission_codes(user, dataset) == [INTEGRATION_SYNC, INTEGRATION_VIEW]

    def test_global_grant_reports_on_every_dataset(self):
        user = baker.make(User)
        grant(user, PERMISSIONS.AGENT.VIEW)
        first = baker.make(DataSet)
        second = baker.make(DataSet)

        assert dataset_permission_codes(user, first) == [AGENT_VIEW]
        assert dataset_permission_codes(user, second) == [AGENT_VIEW]

    def test_global_and_role_grants_are_unioned_without_duplicates(self):
        user = baker.make(User)
        grant(user, PERMISSIONS.AGENT.VIEW)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        role.permissions.add(_permission(PERMISSIONS.AGENT.VIEW), _permission(PERMISSIONS.CONVERSATION.CONVERSE))
        baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)

        assert dataset_permission_codes(user, dataset) == [AGENT_VIEW, CONVERSATION_CONVERSE]

    def test_global_only_permissions_are_never_reported(self):
        # `dataset.view` is what makes the dataset visible in the first place, but it is global-only:
        # it says nothing about what can be done inside this dataset, so it stays off this list.
        user = baker.make(User)
        grant(user, PERMISSIONS.DATASET.VIEW)
        dataset = baker.make(DataSet)

        assert DATASET_VIEW not in dataset_permission_codes(user, dataset)
        assert dataset_permission_codes(user, dataset) == []

    def test_admin_holds_every_dataset_scoped_code_everywhere(self):
        admin = baker.make(User, is_superuser=True)
        first = baker.make(DataSet)
        second = baker.make(DataSet)

        assert set(dataset_permission_codes(admin, first)) == DATASET_SCOPED_CONTRACT
        assert set(dataset_permission_codes(admin, second)) == DATASET_SCOPED_CONTRACT

    def test_plain_user_holds_nothing(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)

        assert dataset_permission_codes(user, dataset) == []

    def test_role_carrying_no_permissions_reports_nothing(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)
        baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=baker.make(DatasetRole))

        assert dataset_permission_codes(user, dataset) == []
