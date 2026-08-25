import re

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from model_bakery import baker

from account.authorization import PERMISSIONS
from account.authorization.backends import RolePermissionsBackend
from account.models import User
from account.tests.helpers import grant, join_global_role, make_global_role
from account.tests.public_permission_codes_contract import DATASET_VIEW, USER_VIEW

pytestmark = pytest.mark.django_db


@pytest.fixture
def backend():
    return RolePermissionsBackend()


class TestPermissionsReachAUserThroughEveryPath:
    """`auth.Group` used to resolve global role membership. These paths are ours now."""

    def test_a_directly_granted_permission_is_held(self, user):
        grant(user, PERMISSIONS.DATASET.VIEW)

        assert user.has_perm(PERMISSIONS.DATASET.VIEW)

    def test_a_permission_carried_by_a_global_role_reaches_its_members(self, user):
        join_global_role(user, make_global_role("viewers", PERMISSIONS.DATASET.VIEW))

        assert user.has_perm(PERMISSIONS.DATASET.VIEW)

    def test_a_non_member_of_the_global_role_does_not_hold_it(self, user):
        make_global_role("viewers", PERMISSIONS.DATASET.VIEW)

        assert not user.has_perm(PERMISSIONS.DATASET.VIEW)

    def test_leaving_a_global_role_gives_up_what_it_carried(self, user):
        global_role = make_global_role("viewers", PERMISSIONS.DATASET.VIEW)
        join_global_role(user, global_role)
        global_role.members.remove(user)

        assert not User.objects.get(pk=user.pk).has_perm(PERMISSIONS.DATASET.VIEW)

    def test_both_paths_at_once_resolve_to_one_union(self, user):
        grant(user, PERMISSIONS.DATASET.VIEW)
        join_global_role(user, make_global_role("viewers", PERMISSIONS.DATASET.VIEW, PERMISSIONS.USER.VIEW))

        codes = user.get_all_permissions()

        assert codes == {PERMISSIONS.DATASET.VIEW, PERMISSIONS.USER.VIEW}

    def test_two_global_roles_carrying_the_same_permission_do_not_double_it(self, user):
        join_global_role(user, make_global_role("viewers", PERMISSIONS.DATASET.VIEW))
        join_global_role(user, make_global_role("readers", PERMISSIONS.DATASET.VIEW))

        assert user.get_all_permissions() == {PERMISSIONS.DATASET.VIEW}

    def test_the_public_codes_a_global_role_carries_reach_the_account_payload(self, user, api_client):
        join_global_role(user, make_global_role("viewers", PERMISSIONS.DATASET.VIEW, PERMISSIONS.USER.VIEW))

        response = api_client.get("/api/account")

        assert sorted(response.data["permissions"]) == sorted([DATASET_VIEW, USER_VIEW])


class TestWhoTheBackendRefusesToAnswerFor:
    def test_a_superuser_short_circuits_before_the_backend_runs(self, backend, admin_user):
        assert admin_user.has_perm(PERMISSIONS.DATASET.VIEW)
        assert backend.get_all_permissions(admin_user) == set()

    def test_an_inactive_user_holds_nothing(self, backend):
        user = baker.make(User, is_active=False)
        join_global_role(user, make_global_role("viewers", PERMISSIONS.DATASET.VIEW))

        assert backend.get_all_permissions(user) == set()
        assert not user.has_perm(PERMISSIONS.DATASET.VIEW)

    def test_an_anonymous_user_holds_nothing(self, backend):
        assert backend.get_all_permissions(AnonymousUser()) == set()

    def test_object_level_questions_are_not_this_backend_s_business(self, backend, user, data_set):
        join_global_role(user, make_global_role("viewers", PERMISSIONS.DATASET.VIEW))

        assert backend.get_all_permissions(user, obj=data_set) == set()


class TestTheLookupIsCachedOnTheUser:
    def test_repeated_questions_cost_one_query(self, backend, user, django_assert_num_queries):
        join_global_role(user, make_global_role("viewers", PERMISSIONS.DATASET.VIEW))

        with django_assert_num_queries(1):
            backend.get_all_permissions(user)
            backend.get_all_permissions(user)
            backend.has_perm(user, PERMISSIONS.DATASET.VIEW)
            backend.has_perm(user, PERMISSIONS.USER.VIEW)


def _project_sources(*, excluding: str) -> list:
    return [
        path for path in settings.BASE_DIR.rglob("*.py") if "migrations" not in path.parts and path.name != excluding
    ]


class TestAuthGroupIsRetired:
    """`auth_group` survives only because `PermissionsMixin` declares `User.groups`. It is empty,
    nothing reads it, and the rule that keeps it that way is that nobody imports the model."""

    def test_nothing_imports_django_s_group_model(self):
        reference = re.compile(r"auth\.models import [^\n]*\bGroup\b|auth\.models\.Group|[\"']auth\.Group[\"']")

        offenders = [
            str(path.relative_to(settings.BASE_DIR))
            for path in _project_sources(excluding="test_backends.py")
            if reference.search(path.read_text())
        ]

        assert offenders == []

    def test_nothing_calls_with_perm(self):
        """`ModelBackend.with_perm` answers "which users hold this permission" through
        `user_permissions` and `groups`, so after this refactor it silently omits everyone holding
        a permission through a global role. The fix belongs with the first caller that needs the
        reverse lookup; until then there are none, and this keeps it that way."""
        call = re.compile(r"\bwith_perm\b")

        offenders = [
            str(path.relative_to(settings.BASE_DIR))
            for path in _project_sources(excluding="test_backends.py")
            if call.search(path.read_text())
        ]

        assert offenders == []
