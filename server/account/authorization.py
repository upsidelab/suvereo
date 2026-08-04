from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from guardian.shortcuts import assign_perm, remove_perm

ADMIN_GROUP_NAME = "Admin"

PERM_MANAGE_USERS = "account.manage_users"
PERM_VIEW_USERS = "account.view_users"
PERM_MANAGE_SERVICE_ACCOUNTS = "account.manage_service_accounts"
PERM_VIEW_SERVICE_ACCOUNTS = "account.view_service_accounts"
PERM_MANAGE_DATASETS = "catalog.manage_datasets"
PERM_VIEW_ALL_DATASETS = "catalog.view_all_datasets"
PERM_CONFIGURE_MODELS = "catalog.configure_models"
PERM_MANAGE_AGENTS = "catalog.manage_agents"
PERM_VIEW_INTEGRATIONS = "catalog.view_integrations"
PERM_MANAGE_INTEGRATIONS = "catalog.manage_integrations"
PERM_VIEW_ALL_CONVERSATIONS = "agent.view_all_conversations"

PERM_CONVERSE_ALL_DATASETS = "catalog.converse_all_datasets"
PERM_MANAGE_ALL_AGENTS = "catalog.manage_all_agents"
PERM_VIEW_ALL_INTEGRATIONS = "catalog.view_all_integrations"
PERM_MANAGE_ALL_INTEGRATIONS = "catalog.manage_all_integrations"

ADMIN_GROUP_PERMISSIONS = [
    PERM_MANAGE_USERS,
    PERM_VIEW_USERS,
    PERM_MANAGE_SERVICE_ACCOUNTS,
    PERM_VIEW_SERVICE_ACCOUNTS,
    PERM_MANAGE_DATASETS,
    PERM_VIEW_ALL_DATASETS,
    PERM_CONFIGURE_MODELS,
    PERM_VIEW_ALL_CONVERSATIONS,
    PERM_CONVERSE_ALL_DATASETS,
    PERM_MANAGE_ALL_AGENTS,
    PERM_VIEW_ALL_INTEGRATIONS,
    PERM_MANAGE_ALL_INTEGRATIONS,
]

PERM_VIEW_DATASET = "catalog.view_dataset"
PERM_CONVERSE = "catalog.converse"

DATASET_PERMISSION_CODENAMES = [
    PERM_VIEW_DATASET,
    PERM_MANAGE_AGENTS,
    PERM_CONVERSE,
    PERM_VIEW_INTEGRATIONS,
    PERM_MANAGE_INTEGRATIONS,
]

DATASET_PERMISSION_GLOBAL_COUNTERPART = {
    PERM_VIEW_DATASET: PERM_VIEW_ALL_DATASETS,
    PERM_MANAGE_AGENTS: PERM_MANAGE_ALL_AGENTS,
    PERM_CONVERSE: PERM_CONVERSE_ALL_DATASETS,
    PERM_VIEW_INTEGRATIONS: PERM_VIEW_ALL_INTEGRATIONS,
    PERM_MANAGE_INTEGRATIONS: PERM_MANAGE_ALL_INTEGRATIONS,
}
"""Every dataset-scoped permission has a global "_all_datasets"-style counterpart, mirroring
catalog.view_dataset/catalog.view_all_datasets -- checked by has_dataset_perm below, so every
existing call site benefits automatically without touching each one individually."""

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


def grant_full_dataset_access(target, dataset) -> None:
    """Grant `target` (a User or Group) every dataset-scoped permission on `dataset` directly.

    Used where full access must be granted unconditionally (dataset creation, service-account
    provisioning) -- these call sites must not depend on a "editor"-named DatasetRole still
    existing, since DatasetRole rows (including the seeded ones) are user-deletable.
    """
    for codename in DATASET_PERMISSION_CODENAMES:
        assign_perm(codename, target, dataset)


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


def revoke_dataset_role_everywhere(role_name: str) -> int:
    """Revoke every (target, dataset) grant currently matching this role's exact permission set.

    Called just before deleting a DatasetRole so no orphaned guardian grants survive the role
    definition disappearing -- mirrors how deleting a Group cascades its GroupObjectPermission
    rows, except DatasetRole grants aren't stored via a foreign key to DatasetRole, so this has
    to walk the same (target, dataset) search count_datasets_using_role uses and revoke instead
    of counting. Returns how many (target, dataset) pairs were revoked.
    """
    from guardian.shortcuts import get_groups_with_perms, get_users_with_perms

    from account.models import DatasetRole
    from catalog.models import DataSet

    role = DatasetRole.objects.get(name=role_name)
    role_codenames = {p.codename for p in role.permissions.all()}

    count = 0
    for dataset in DataSet.objects.all():
        for user, codenames in get_users_with_perms(dataset, attach_perms=True, with_group_users=False).items():
            if set(codenames) == role_codenames:
                remove_all_dataset_grants(user, dataset)
                count += 1
        for group, codenames in get_groups_with_perms(dataset, attach_perms=True).items():
            if set(codenames) == role_codenames:
                remove_all_dataset_grants(group, dataset)
                count += 1
    return count


def has_dataset_perm(user, codename: str, dataset) -> bool:
    """True if user holds `codename`'s global "_all_datasets" counterpart (if it has one, see
    DATASET_PERMISSION_GLOBAL_COUNTERPART), holds `codename` itself globally, or holds it
    scoped to this dataset.

    The only sanctioned way to check a dataset-scoped capability — a bare
    ``user.has_perm(codename)`` silently excludes every per-dataset grantee.
    Must only be called with a codename whose Permission.content_type is
    DataSet — never a permission defined on a different model, or guardian
    raises WrongAppError.
    """
    global_counterpart = DATASET_PERMISSION_GLOBAL_COUNTERPART.get(codename)
    if global_counterpart and user.has_perm(global_counterpart):
        return True
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


def _admin_equivalent_group_ids() -> set:
    """IDs of every group whose membership grants Admin-equivalent power.

    That's the ``Admin`` group itself, plus any group holding ``manage_users`` or
    ``manage_service_accounts`` — holding either permission already lets its holder repeat
    this same self-escalation by assigning a *different* group through the same code path.
    """
    grants_sensitive_permission = Q(
        permissions__content_type__app_label="account", permissions__codename="manage_users"
    ) | Q(permissions__content_type__app_label="account", permissions__codename="manage_service_accounts")
    return set(Group.objects.filter(Q(name=ADMIN_GROUP_NAME) | grants_sensitive_permission).values_list("id", flat=True))


def assert_group_ids_assignable(requesting_user, group_ids) -> None:
    """Raise if `requesting_user` is a non-Admin attempting to assign an Admin-equivalent group.

    Group membership is how ``is_application_admin`` decides admin status, but assigning a
    ``group_id`` on the User/ServiceAccount write paths is only gated by the delegable
    ``manage_users``/``manage_service_accounts`` permissions. Without this check, a non-Admin
    holding either permission could self-promote (or promote a service account) to full
    application admin by assigning the Admin group directly, or any other group that grants
    one of those two permissions. Admin-group members (and superusers) may assign any group
    freely — they already hold full authority.
    """
    if is_application_admin(requesting_user):
        return
    forbidden_ids = _admin_equivalent_group_ids() & set(group_ids)
    if forbidden_ids:
        raise DjangoValidationError("Only an Admin can grant Admin-equivalent group membership.")
