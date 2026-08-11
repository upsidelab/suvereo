import pytest
from django.contrib.auth.models import Group, Permission
from model_bakery import baker
from rest_framework.exceptions import PermissionDenied

from account.authorization import PERMISSIONS
from account.authorization.decorators import (
    any_global_permission_required,
    any_permission_on_any_dataset_required,
    global_permission_required,
)
from account.models import DatasetGroupRoleAssignment, DatasetRole, DatasetUserRoleAssignment, User
from catalog.models import DataSet

pytestmark = pytest.mark.django_db


def _permission(codename: str) -> Permission:
    app_label, name = codename.split(".")
    return Permission.objects.get(codename=name, content_type__app_label=app_label)


class _FakeRequest:
    def __init__(self, user):
        self.user = user


class _FakeView:
    def __init__(self, user):
        self.request = _FakeRequest(user)

    def permission_denied(self, request, message=None, code=None):
        raise PermissionDenied(detail=message, code=code)

    @global_permission_required(PERMISSIONS.DATASET.ADD)
    def single_permission_action(self, *args, **kwargs):
        return "single-ok"

    @any_global_permission_required(PERMISSIONS.DATASET.ADD, PERMISSIONS.DATASET.CHANGE)
    def any_permission_action(self, *args, **kwargs):
        return "any-ok"

    @any_permission_on_any_dataset_required(PERMISSIONS.AGENT.ADD, PERMISSIONS.AGENT.CHANGE)
    def any_dataset_permission_action(self, *args, **kwargs):
        return "any-dataset-ok"


class TestGlobalPermissionRequired:
    def test_preserves_wrapped_method_metadata(self):
        assert _FakeView.single_permission_action.__name__ == "single_permission_action"

    def test_allows_holder_of_the_permission(self):
        user = baker.make(User)
        user.user_permissions.add(_permission(PERMISSIONS.DATASET.ADD))
        view = _FakeView(user)

        assert view.single_permission_action() == "single-ok"

    def test_allows_superuser_without_explicit_grant(self):
        user = baker.make(User, is_superuser=True)
        view = _FakeView(user)

        assert view.single_permission_action() == "single-ok"

    def test_denies_user_without_the_permission(self):
        user = baker.make(User)
        view = _FakeView(user)

        with pytest.raises(PermissionDenied):
            view.single_permission_action()

    def test_denied_case_does_not_execute_the_wrapped_method(self):
        calls = []

        class _View(_FakeView):
            @global_permission_required(PERMISSIONS.DATASET.ADD)
            def action(self, *args, **kwargs):
                calls.append(1)
                return "ok"

        view = _View(baker.make(User))

        with pytest.raises(PermissionDenied):
            view.action()

        assert calls == []


class TestAnyGlobalPermissionRequired:
    def test_allows_holder_of_first_codename(self):
        user = baker.make(User)
        user.user_permissions.add(_permission(PERMISSIONS.DATASET.ADD))
        view = _FakeView(user)

        assert view.any_permission_action() == "any-ok"

    def test_allows_holder_of_second_codename(self):
        user = baker.make(User)
        user.user_permissions.add(_permission(PERMISSIONS.DATASET.CHANGE))
        view = _FakeView(user)

        assert view.any_permission_action() == "any-ok"

    def test_allows_holder_of_both_codenames(self):
        user = baker.make(User)
        user.user_permissions.add(_permission(PERMISSIONS.DATASET.ADD))
        user.user_permissions.add(_permission(PERMISSIONS.DATASET.CHANGE))
        view = _FakeView(user)

        assert view.any_permission_action() == "any-ok"

    def test_allows_superuser(self):
        user = baker.make(User, is_superuser=True)
        view = _FakeView(user)

        assert view.any_permission_action() == "any-ok"

    def test_denies_holder_of_neither_codename(self):
        user = baker.make(User)
        view = _FakeView(user)

        with pytest.raises(PermissionDenied):
            view.any_permission_action()


class TestAnyPermissionOnAnyDatasetRequired:
    def test_allows_global_holder(self):
        user = baker.make(User)
        user.user_permissions.add(_permission(PERMISSIONS.AGENT.ADD))
        view = _FakeView(user)

        assert view.any_dataset_permission_action() == "any-dataset-ok"

    def test_allows_holder_via_role_on_any_dataset(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        role.permissions.add(_permission(PERMISSIONS.AGENT.CHANGE))
        baker.make(DatasetUserRoleAssignment, user=user, dataset=dataset, role=role)
        view = _FakeView(user)

        assert view.any_dataset_permission_action() == "any-dataset-ok"

    def test_allows_holder_via_group_role_on_any_dataset(self):
        user = baker.make(User)
        group = baker.make(Group)
        user.groups.add(group)
        dataset = baker.make(DataSet)
        role = baker.make(DatasetRole)
        role.permissions.add(_permission(PERMISSIONS.AGENT.ADD))
        baker.make(DatasetGroupRoleAssignment, group=group, dataset=dataset, role=role)
        view = _FakeView(user)

        assert view.any_dataset_permission_action() == "any-dataset-ok"

    def test_allows_superuser(self):
        user = baker.make(User, is_superuser=True)
        view = _FakeView(user)

        assert view.any_dataset_permission_action() == "any-dataset-ok"

    def test_denies_holder_of_neither_codename_anywhere(self):
        user = baker.make(User)
        view = _FakeView(user)

        with pytest.raises(PermissionDenied):
            view.any_dataset_permission_action()
