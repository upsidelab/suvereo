import re

import pytest
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import AnonymousUser
from model_bakery import baker

from account.authorization import GLOBAL_SCOPE_PERMISSIONS, PERMISSIONS
from account.authorization.backends import RoleBackend
from account.models import User
from account.tests.helpers import join_global_role, join_group, make_global_role, make_group, permission
from account.tests.public_permission_codes_contract import DATASET_VIEW, USER_VIEW

pytestmark = pytest.mark.django_db


@pytest.fixture
def backend():
    return RoleBackend()


class TestAGlobalRoleIsTheOnlyWayAPermissionReachesAnAccount:
    def test_a_permission_written_straight_onto_the_account_has_no_effect(self, user):
        """No endpoint writes `user.user_permissions`, so one that had been written by hand is a
        grant the product cannot make, cannot show and cannot revoke. It resolves to nothing."""
        user.user_permissions.add(permission(PERMISSIONS.DATASET.VIEW))

        assert not user.has_perm(PERMISSIONS.DATASET.VIEW)
        assert user.get_all_permissions() == set()

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

    def test_two_global_roles_carrying_the_same_permission_do_not_double_it(self, user):
        join_global_role(user, make_global_role("viewers", PERMISSIONS.DATASET.VIEW))
        join_global_role(user, make_global_role("readers", PERMISSIONS.DATASET.VIEW))

        assert user.get_all_permissions() == {PERMISSIONS.DATASET.VIEW}

    def test_the_public_codes_a_global_role_carries_reach_the_account_payload(self, user, api_client):
        join_global_role(user, make_global_role("viewers", PERMISSIONS.DATASET.VIEW, PERMISSIONS.USER.VIEW))

        response = api_client.get("/api/account")

        assert sorted(response.data["permissions"]) == sorted([DATASET_VIEW, USER_VIEW])


class TestAGroupCarriesTheGlobalRolesItHolds:
    def test_a_permission_a_group_s_global_role_carries_reaches_the_group_s_members(self, user):
        join_group(user, make_group("contractors", make_global_role("viewers", PERMISSIONS.DATASET.VIEW)))

        assert user.has_perm(PERMISSIONS.DATASET.VIEW)

    def test_a_non_member_of_the_group_does_not_hold_it(self, user):
        make_group("contractors", make_global_role("viewers", PERMISSIONS.DATASET.VIEW))

        assert not user.has_perm(PERMISSIONS.DATASET.VIEW)

    def test_a_group_holding_no_global_role_carries_nothing(self, user):
        join_group(user, make_group("contractors"))

        assert user.get_all_permissions() == set()

    def test_leaving_the_group_gives_up_what_it_carried(self, user):
        group = make_group("contractors", make_global_role("viewers", PERMISSIONS.DATASET.VIEW))
        join_group(user, group)
        group.members.remove(user)

        assert not User.objects.get(pk=user.pk).has_perm(PERMISSIONS.DATASET.VIEW)

    def test_revoking_the_global_role_from_the_group_gives_it_up_too(self, user):
        global_role = make_global_role("viewers", PERMISSIONS.DATASET.VIEW)
        group = make_group("contractors", global_role)
        join_group(user, group)
        group.global_roles.remove(global_role)

        assert not User.objects.get(pk=user.pk).has_perm(PERMISSIONS.DATASET.VIEW)

    def test_the_two_paths_union_and_neither_shadows_the_other(self, user):
        direct = make_global_role("viewers", PERMISSIONS.DATASET.VIEW)
        join_global_role(user, direct)
        join_group(user, make_group("contractors", make_global_role("auditors", PERMISSIONS.USER.VIEW)))

        assert user.get_all_permissions() == {PERMISSIONS.DATASET.VIEW, PERMISSIONS.USER.VIEW}

    def test_the_same_global_role_held_both_ways_is_not_doubled(self, user):
        global_role = make_global_role("viewers", PERMISSIONS.DATASET.VIEW)
        join_global_role(user, global_role)
        join_group(user, make_group("contractors", global_role))

        assert user.get_all_permissions() == {PERMISSIONS.DATASET.VIEW}

    def test_losing_one_path_leaves_the_other_in_force(self, user):
        global_role = make_global_role("viewers", PERMISSIONS.DATASET.VIEW)
        join_global_role(user, global_role)
        group = make_group("contractors", global_role)
        join_group(user, group)

        group.members.remove(user)

        assert User.objects.get(pk=user.pk).has_perm(PERMISSIONS.DATASET.VIEW)


class TestAuthenticationIsStillDjangoS:
    """The one backend in `AUTHENTICATION_BACKENDS` is also the one that checks passwords."""

    def test_credentials_still_resolve_to_their_account(self):
        user = baker.make(User, email="who@example.com")
        user.set_password("s3cret-pass")
        user.save()

        assert authenticate(username="who@example.com", password="s3cret-pass") == user

    def test_a_wrong_password_resolves_to_nobody(self):
        user = baker.make(User, email="who@example.com")
        user.set_password("s3cret-pass")
        user.save()

        assert authenticate(username="who@example.com", password="wrong") is None


class TestWhoTheBackendRefusesToAnswerFor:
    def test_a_superuser_holds_everything_without_belonging_to_a_role(self, admin_user):
        """`has_perm` short-circuits in `PermissionsMixin`, but `get_all_permissions` does not -
        an admin's catalog comes from `ModelBackend`'s superuser branch, above the two hooks this
        backend replaces. It is what `AccountSerializer.permissions` reports to the frontend."""
        assert admin_user.has_perm(PERMISSIONS.DATASET.VIEW)
        assert admin_user.get_all_permissions() >= set(GLOBAL_SCOPE_PERMISSIONS)

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
    """`auth_group` outlives this refactor only because `django.contrib.auth` recreates it on every
    fresh database. Nothing here can reach it: the accessor is gone from the model, and the rule
    that keeps it that way is that nobody imports it."""

    def test_the_user_model_has_no_accessor_onto_it(self, user):
        """`PermissionsMixin` declares `User.groups`, and leaving it in place would have left an
        always-empty queryset ready to answer as though it knew about global roles. Setting it to
        `None` drops the field; the name survives as a plain `None`, so reaching for it raises."""
        assert "groups" not in {field.name for field in User._meta.get_fields()}

        with pytest.raises(AttributeError):
            user.groups.all()

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
