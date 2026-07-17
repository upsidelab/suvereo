from django.contrib.auth.models import Group

ADMIN_GROUP_NAME = "Admin"

PERM_MANAGE_USERS = "account.manage_users"
PERM_MANAGE_SERVICE_ACCOUNTS = "account.manage_service_accounts"
PERM_MANAGE_DATASETS = "catalog.manage_datasets"
PERM_ACCESS_ALL_DATASETS = "catalog.access_all_datasets"
PERM_CONFIGURE_MODELS = "catalog.configure_models"

ADMIN_GROUP_PERMISSIONS = [
    PERM_MANAGE_USERS,
    PERM_MANAGE_SERVICE_ACCOUNTS,
    PERM_MANAGE_DATASETS,
    PERM_ACCESS_ALL_DATASETS,
    PERM_CONFIGURE_MODELS,
]


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
