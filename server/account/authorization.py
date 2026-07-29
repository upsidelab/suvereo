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

DATASET_PERMISSION_CODENAMES = [PERM_ACCESS_DATASET, PERM_MANAGE_AGENTS]

GLOBAL_PERMISSION_CODENAMES = ADMIN_GROUP_PERMISSIONS
"""Same list as ADMIN_GROUP_PERMISSIONS today (Admin holds every global permission), but
conceptually distinct: this is "what the role composer may offer", not "what Admin has"."""


def assign_dataset_role(target, dataset, role_name: str) -> None:
    """Grant `target` (a User or Group) the named role's permission bundle on `dataset`."""
    from account.models import DatasetRole

    role = DatasetRole.objects.get(name=role_name)
    for permission in role.permissions.all():
        assign_perm(f"{permission.content_type.app_label}.{permission.codename}", target, dataset)


def remove_dataset_role(target, dataset, role_name: str) -> None:
    """Revoke the named role's permission bundle from `target` on `dataset`."""
    from account.models import DatasetRole

    role = DatasetRole.objects.get(name=role_name)
    for permission in role.permissions.all():
        remove_perm(f"{permission.content_type.app_label}.{permission.codename}", target, dataset)


def remove_all_dataset_grants(target, dataset) -> None:
    """Revoke every dataset-role permission this target holds on `dataset`, regardless of role."""
    for codename in DATASET_PERMISSION_CODENAMES:
        remove_perm(codename, target, dataset)


def count_datasets_using_role(role_name: str) -> int:
    """Count (target, dataset) grants whose codename set exactly matches this role's.

    guardian stores raw (target, permission, dataset) grants, not role names, so a role is
    "in use" when some target's granted codename set on some dataset matches this role's
    codename set exactly — the same reasoning catalog.views._resolve_dataset_role uses to
    go the other direction (codenames -> role name).
    """
    from guardian.shortcuts import get_groups_with_perms, get_users_with_perms

    from account.models import DatasetRole
    from catalog.models import DataSet

    role = DatasetRole.objects.get(name=role_name)
    role_codenames = {p.codename for p in role.permissions.all()}

    count = 0
    for dataset in DataSet.objects.all():
        for _, codenames in get_users_with_perms(dataset, attach_perms=True, with_group_users=False).items():
            if set(codenames) == role_codenames:
                count += 1
        for _, codenames in get_groups_with_perms(dataset, attach_perms=True).items():
            if set(codenames) == role_codenames:
                count += 1
    return count


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
