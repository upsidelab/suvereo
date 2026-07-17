import pytest
from django.contrib.auth.models import Group
from model_bakery import baker

from account.authorization import (
    ADMIN_GROUP_NAME,
    ADMIN_GROUP_PERMISSIONS,
    is_application_admin,
    set_application_admin,
)
from account.models import User


@pytest.mark.django_db
class TestAdminGroupMigration:
    def test_admin_group_exists_with_expected_permissions(self):
        group = Group.objects.get(name=ADMIN_GROUP_NAME)
        granted = {f"{p.content_type.app_label}.{p.codename}" for p in group.permissions.all()}
        assert granted == set(ADMIN_GROUP_PERMISSIONS)


@pytest.mark.django_db
class TestApplicationAdmin:
    def test_group_member_is_application_admin(self):
        user = baker.make(User)
        set_application_admin(user, True)
        assert is_application_admin(user) is True

    def test_set_application_admin_false_removes_membership(self):
        user = baker.make(User)
        set_application_admin(user, True)
        set_application_admin(user, False)
        assert is_application_admin(user) is False
        assert not user.groups.filter(name=ADMIN_GROUP_NAME).exists()

    def test_superuser_is_application_admin_without_group(self):
        user = baker.make(User, is_superuser=True)
        assert is_application_admin(user) is True

    def test_staff_only_user_is_not_application_admin(self):
        user = baker.make(User, is_staff=True)
        assert is_application_admin(user) is False

    def test_is_admin_property_reflects_group_membership(self):
        user = baker.make(User)
        assert user.is_admin is False
        set_application_admin(user, True)
        assert user.is_admin is True
