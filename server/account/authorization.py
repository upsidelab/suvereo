from django.contrib.auth.models import Group
from guardian.shortcuts import assign_perm, remove_perm

ADMIN_GROUP_NAME = "Admin"

PERM_MANAGE_USERS = "account.manage_users"
PERM_MANAGE_SERVICE_ACCOUNTS = "account.manage_service_accounts"
PERM_MANAGE_DATASETS = "catalog.manage_datasets"
PERM_ACCESS_ALL_DATASETS = "catalog.access_all_datasets"
PERM_CONFIGURE_MODELS = "catalog.configure_models"
PERM_MANAGE_AGENTS = "catalog.manage_agents"

ADMIN_GROUP_PERMISSIONS = [
    PERM_MANAGE_USERS,
    PERM_MANAGE_SERVICE_ACCOUNTS,
    PERM_MANAGE_DATASETS,
    PERM_ACCESS_ALL_DATASETS,
    PERM_CONFIGURE_MODELS,
    PERM_MANAGE_AGENTS,
]

PERM_ACCESS_DATASET = "catalog.access_dataset"

DATASET_ROLES = {
    "viewer": [PERM_ACCESS_DATASET],
    "editor": [PERM_ACCESS_DATASET, PERM_MANAGE_AGENTS],
}

ALL_DATASET_ROLE_PERMS = {codename for perms in DATASET_ROLES.values() for codename in perms}


def assign_dataset_role(target, dataset, role_name: str) -> None:
    """Grant `target` (a User or Group) the named role's permission bundle on `dataset`."""
    for codename in DATASET_ROLES[role_name]:
        assign_perm(codename, target, dataset)


def remove_dataset_role(target, dataset, role_name: str) -> None:
    """Revoke the named role's permission bundle from `target` on `dataset`."""
    for codename in DATASET_ROLES[role_name]:
        remove_perm(codename, target, dataset)


def remove_all_dataset_grants(target, dataset) -> None:
    """Revoke every dataset-role permission this target holds on `dataset`, regardless of role."""
    for codename in ALL_DATASET_ROLE_PERMS:
        remove_perm(codename, target, dataset)


def has_dataset_perm(user, codename: str, dataset) -> bool:
    """True if user holds `codename` globally, or scoped to this dataset.

    The only sanctioned way to check a dataset-scoped capability — a bare
    ``user.has_perm(codename)`` silently excludes every per-dataset grantee.
    Must only be called with a codename whose Permission.content_type is
    DataSet (today: access_dataset or manage_agents) — never a permission
    defined on a different model, or guardian raises WrongAppError.
    """
    return user.has_perm(codename) or user.has_perm(codename, dataset)


def is_application_admin(user) -> bool:
    """Return True when the user is an application administrator.

    Application admin means membership in the ``Admin`` group or being a Django
    superuser. Intentionally independent from ``is_staff``, which is reserved
    for Django admin-site access.
    """
    return user.is_superuser or user.groups.filter(name=ADMIN_GROUP_NAME).exists()


def set_application_admin(user, enabled: bool) -> None:
    """Add the user to (or remove them from) the ``Admin`` group.

    Raises ``Group.DoesNotExist`` when migrations have not created the group —
    failing loudly beats silently granting nothing.
    """
    group = Group.objects.get(name=ADMIN_GROUP_NAME)
    if enabled:
        user.groups.add(group)
    else:
        user.groups.remove(group)
