"""Factories shared by the permission tests.

These take `PERMISSIONS` members (`PERMISSIONS.USER.VIEW`), not public codes.

Public codes belong in request bodies and response assertions, where they are the contract being
asserted. Import those from `public_permission_codes_contract`.
"""

from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from account.models import (
    DatasetGlobalRoleAssignment,
    DatasetGroupRoleAssignment,
    DatasetRole,
    DatasetUserRoleAssignment,
    GlobalRole,
    UserGroup,
)

# Django caches a user's resolved permissions on the instance, and `force_authenticate` hands that
# same instance to the view. Granting anything after the first `has_perm` therefore has to drop the
# cache, or the new grant is invisible for the rest of the test.
_PERMISSION_CACHES = ("_perm_cache", "_user_perm_cache", "_group_perm_cache")


def _reset_permission_cache(user):
    for cache in _PERMISSION_CACHES:
        user.__dict__.pop(cache, None)
    return user


def permission(codename: str) -> Permission:
    """The `Permission` row for a `PERMISSIONS` member, looked up on `app_label.codename`."""
    app_label, bare_codename = codename.split(".")
    return Permission.objects.get(content_type__app_label=app_label, codename=bare_codename)


def permissions(*codenames: str) -> list[Permission]:
    """The `Permission` rows for a set of `PERMISSIONS` members."""
    return [permission(codename) for codename in codenames]


def grant(user, *codenames: str):
    """Grant global permissions to a user, through a global role kept for them alone.

    Permissions reach an account through global roles and nothing else, so writing them onto
    `user.user_permissions` would grant a test something the product cannot grant anyone.
    Repeated calls accumulate on the same role.
    """
    global_role, _ = GlobalRole.objects.get_or_create(name=f"granted-to-{user.pk}")
    global_role.permissions.add(*permissions(*codenames))
    global_role.members.add(user)
    return _reset_permission_cache(user)


def make_global_role(name: str = "global-role", *codenames: str) -> GlobalRole:
    """A global role carrying the given global permissions."""
    global_role = GlobalRole.objects.create(name=name)
    if codenames:
        global_role.permissions.add(*permissions(*codenames))
    return global_role


def join_global_role(user, global_role: GlobalRole):
    """Add a user to a global role, so the role's permissions reach them."""
    global_role.members.add(user)
    return _reset_permission_cache(user)


def make_group(name: str = "group", *global_roles: GlobalRole) -> UserGroup:
    """A group holding the given global roles."""
    group = UserGroup.objects.create(name=name)
    if global_roles:
        group.global_roles.add(*global_roles)
    return group


def join_group(user, group: UserGroup):
    """Add a user to a group, so everything the group holds reaches them."""
    group.members.add(user)
    return _reset_permission_cache(user)


def make_role(name: str = "role", *codenames: str) -> DatasetRole:
    """A dataset role carrying the given dataset-scoped permissions."""
    role = DatasetRole.objects.create(name=name)
    if codenames:
        role.permissions.add(*permissions(*codenames))
    return role


def assign_role(subject, dataset, role: DatasetRole):
    """Grant `role` on `dataset` to a user, a group or a global role, whichever `subject` is."""
    if isinstance(subject, GlobalRole):
        return DatasetGlobalRoleAssignment.objects.create(global_role=subject, dataset=dataset, role=role)
    if isinstance(subject, UserGroup):
        return DatasetGroupRoleAssignment.objects.create(group=subject, dataset=dataset, role=role)
    return DatasetUserRoleAssignment.objects.create(user=subject, dataset=dataset, role=role)


def client_for(user) -> APIClient:
    """An API client authenticated as `user`."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client
