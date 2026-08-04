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

GLOBAL_PERMISSION_CODENAMES = [
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
"""Every permission a Group can hold globally -- what the Global Role composer may offer, and
what Admin ends up holding in full."""

PERM_VIEW_DATASET = "catalog.view_dataset"
PERM_CONVERSE = "catalog.converse"

DATASET_PERMISSION_GLOBAL_COUNTERPART = {
    PERM_VIEW_DATASET: PERM_VIEW_ALL_DATASETS,
    PERM_MANAGE_AGENTS: PERM_MANAGE_ALL_AGENTS,
    PERM_CONVERSE: PERM_CONVERSE_ALL_DATASETS,
    PERM_VIEW_INTEGRATIONS: PERM_VIEW_ALL_INTEGRATIONS,
    PERM_MANAGE_INTEGRATIONS: PERM_MANAGE_ALL_INTEGRATIONS,
}
"""Every dataset-scoped permission, mapped to its global "_all_datasets"-style counterpart --
checked by has_dataset_perm below, so every existing call site benefits automatically without
touching each one individually. DATASET_PERMISSION_CODENAMES is just this dict's keys, so the
two can't drift out of sync."""

DATASET_PERMISSION_CODENAMES = list(DATASET_PERMISSION_GLOBAL_COUNTERPART)


def assign_dataset_role(target, dataset, role_name: str) -> None:
    """Grant `target` (a User or Group) the named role's permission bundle on `dataset`, and
    record that this role produced the grant -- see DatasetUserRoleAssignment for why."""
    from account.models import DatasetGroupRoleAssignment, DatasetRole, DatasetUserRoleAssignment

    role = DatasetRole.objects.get(name=role_name)
    for permission in role.permissions.all():
        assign_perm(f"{permission.content_type.app_label}.{permission.codename}", target, dataset)

    if isinstance(target, Group):
        DatasetGroupRoleAssignment.objects.update_or_create(group=target, dataset=dataset, defaults={"role": role})
    else:
        DatasetUserRoleAssignment.objects.update_or_create(user=target, dataset=dataset, defaults={"role": role})


def remove_all_dataset_grants(target, dataset) -> None:
    """Revoke every dataset-role permission this target holds on `dataset`, regardless of role,
    and clear any recorded role assignment for it."""
    from account.models import DatasetGroupRoleAssignment, DatasetUserRoleAssignment

    for codename in DATASET_PERMISSION_CODENAMES:
        remove_perm(codename, target, dataset)

    if isinstance(target, Group):
        DatasetGroupRoleAssignment.objects.filter(group=target, dataset=dataset).delete()
    else:
        DatasetUserRoleAssignment.objects.filter(user=target, dataset=dataset).delete()


def grant_full_dataset_access(target, dataset) -> None:
    """Grant `target` (a User or Group) every dataset-scoped permission on `dataset` directly.

    Used where full access must be granted unconditionally (dataset creation, service-account
    provisioning) -- these call sites must not depend on a "editor"-named DatasetRole still
    existing, since DatasetRole rows (including the seeded ones) are user-deletable.
    """
    for codename in DATASET_PERMISSION_CODENAMES:
        assign_perm(codename, target, dataset)


def count_datasets_using_role(role_name: str) -> int:
    """Count (target, dataset) grants currently assigned this role."""
    from account.models import DatasetGroupRoleAssignment, DatasetRole, DatasetUserRoleAssignment

    role = DatasetRole.objects.get(name=role_name)
    return (
        DatasetUserRoleAssignment.objects.filter(role=role).count()
        + DatasetGroupRoleAssignment.objects.filter(role=role).count()
    )


def revoke_dataset_role_everywhere(role_name: str) -> int:
    """Revoke this role from every (target, dataset) grant currently assigned it.

    Called just before deleting a DatasetRole so no orphaned guardian grants survive the role
    definition disappearing -- mirrors how deleting a Group cascades its GroupObjectPermission
    rows. Returns how many (target, dataset) pairs were revoked.
    """
    from account.models import DatasetGroupRoleAssignment, DatasetRole, DatasetUserRoleAssignment

    role = DatasetRole.objects.get(name=role_name)
    count = 0
    for assignment in DatasetUserRoleAssignment.objects.filter(role=role).select_related("dataset"):
        remove_all_dataset_grants(assignment.user, assignment.dataset)
        count += 1
    for assignment in DatasetGroupRoleAssignment.objects.filter(role=role).select_related("dataset"):
        remove_all_dataset_grants(assignment.group, assignment.dataset)
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
        permissions__content_type__app_label="account",
        permissions__codename__in=["manage_users", "manage_service_accounts"],
    )
    admin_equivalent_groups = Group.objects.filter(Q(name=ADMIN_GROUP_NAME) | grants_sensitive_permission)
    return set(admin_equivalent_groups.values_list("id", flat=True))


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
