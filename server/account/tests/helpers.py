"""Factories shared by the permission tests.

These take `PERMISSIONS` members (`PERMISSIONS.USER.VIEW`), not public codes.

Public codes belong in request bodies and response assertions, where they are the contract being
asserted. Import those from `public_permission_codes_contract`.
"""

from django.contrib.auth.models import Group, Permission
from rest_framework.test import APIClient

from account.models import DatasetGroupRoleAssignment, DatasetRole, DatasetUserRoleAssignment

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
    """Grant global permissions directly to a user."""
    user.user_permissions.add(*permissions(*codenames))
    return _reset_permission_cache(user)


def make_group(name: str = "group", *codenames: str) -> Group:
    """A group carrying the given global permissions."""
    group = Group.objects.create(name=name)
    if codenames:
        group.permissions.add(*permissions(*codenames))
    return group


def join_group(user, group: Group):
    """Add a user to a group, so the group's permissions reach them."""
    user.groups.add(group)
    return _reset_permission_cache(user)


def make_role(name: str = "role", *codenames: str) -> DatasetRole:
    """A dataset role carrying the given dataset-scoped permissions."""
    role = DatasetRole.objects.create(name=name)
    if codenames:
        role.permissions.add(*permissions(*codenames))
    return role


def assign_role(subject, dataset, role: DatasetRole):
    """Grant `role` on `dataset` to a user or a group, whichever `subject` is."""
    if isinstance(subject, Group):
        return DatasetGroupRoleAssignment.objects.create(group=subject, dataset=dataset, role=role)
    return DatasetUserRoleAssignment.objects.create(user=subject, dataset=dataset, role=role)


def client_for(user) -> APIClient:
    """An API client authenticated as `user`."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client
