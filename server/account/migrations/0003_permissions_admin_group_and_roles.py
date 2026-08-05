import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

ADMIN_GROUP_NAME = "Admin"

# account.user permissions Admin holds globally. Created explicitly via ContentType because the
# post_migrate signal that materializes Meta.permissions has not run yet within this migration.
ACCOUNT_PERMISSIONS = [
    ("manage_users", "Can manage human users"),
    ("view_users", "Can view human users"),
    ("manage_service_accounts", "Can manage service accounts"),
    ("view_service_accounts", "Can view service accounts"),
]

# Human-readable description for every permission across account, catalog and agent.
PERMISSION_DESCRIPTIONS = {
    ("account", "user", "manage_users"): "Can create, edit, and delete user accounts.",
    ("account", "user", "view_users"): "Can see the list of users, without editing.",
    ("account", "user", "manage_service_accounts"): (
        "Can create, edit, and delete service (API) accounts and their tokens."
    ),
    ("account", "user", "view_service_accounts"): "Can see the list of service accounts, without editing.",
    ("catalog", "dataset", "manage_datasets"): "Can create, configure, and delete data sets.",
    ("catalog", "dataset", "view_all_datasets"): (
        "Can see every data set in the system, regardless of per-dataset role assignments."
    ),
    ("catalog", "dataset", "configure_models"): (
        "Can view the configuration of language model providers (e.g. provider keys/parameters)."
    ),
    ("catalog", "dataset", "view_dataset"): (
        "Can browse this data set's catalog. Does not include chatting with its agents."
    ),
    ("catalog", "dataset", "converse"): "Can chat with this data set's agents and see their own message history.",
    ("catalog", "dataset", "manage_agents"): "Can create, configure, and delete this data set's agents.",
    ("catalog", "dataset", "view_integrations"): "Can see this data set's configured integrations.",
    ("catalog", "dataset", "manage_integrations"): "Can add, edit, delete, and sync this data set's integrations.",
    ("catalog", "dataset", "converse_all_datasets"): (
        "Can chat with every data set's agents and see their own message history."
    ),
    ("catalog", "dataset", "manage_all_agents"): "Can create, configure, and delete agents in every data set.",
    ("catalog", "dataset", "view_all_integrations"): "Can see every data set's configured integrations.",
    ("catalog", "dataset", "manage_all_integrations"): (
        "Can add, edit, delete, and sync integrations in every data set."
    ),
    ("agent", "conversation", "view_all_conversations"): (
        "Can view every user's conversations across every data set, not just their own."
    ),
}

# manage_X permission -> the view_X permission it should also check in the composer UI. Used to
# be hardcoded on the frontend (permission-checklist.tsx's MANAGE_IMPLIES_VIEW); this is now the
# single source of truth instead.
IMPLIED_VIEW_PERMISSIONS = {
    ("account", "user", "manage_users"): ("account", "user", "view_users"),
    ("account", "user", "manage_service_accounts"): ("account", "user", "view_service_accounts"),
    ("catalog", "dataset", "manage_datasets"): ("catalog", "dataset", "view_all_datasets"),
    ("catalog", "dataset", "manage_agents"): ("catalog", "dataset", "view_dataset"),
    ("catalog", "dataset", "manage_integrations"): ("catalog", "dataset", "view_integrations"),
    ("catalog", "dataset", "manage_all_agents"): ("catalog", "dataset", "view_all_datasets"),
    ("catalog", "dataset", "manage_all_integrations"): ("catalog", "dataset", "view_all_integrations"),
}

# Dataset-scoped permissions granted per-object via a DatasetRole rather than to Admin directly;
# Admin instead holds each one's global "_all_datasets" counterpart
DATASET_ROLE_PERMISSIONS = {
    "Viewer": ["view_dataset", "converse"],
    "Editor": ["view_dataset", "converse", "manage_agents", "view_integrations", "manage_integrations"],
}


def create_permissions_admin_group_and_roles(apps, schema_editor):
    """Create account's own permissions, describe every permission in the system, seed the
    Admin group and the Viewer/Editor DatasetRole presets, and migrate pre-existing is_staff
    users into Admin.
    """
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    User = apps.get_model("account", "User")
    DatasetRole = apps.get_model("account", "DatasetRole")
    PermissionDescription = apps.get_model("account", "PermissionDescription")

    user_content_type, _ = ContentType.objects.get_or_create(app_label="account", model="user")
    permissions_by_key = {}
    for codename, name in ACCOUNT_PERMISSIONS:
        permission, _ = Permission.objects.get_or_create(
            content_type=user_content_type, codename=codename, defaults={"name": name}
        )
        permissions_by_key[("account", "user", codename)] = permission

    for (app_label, model, codename), description in PERMISSION_DESCRIPTIONS.items():
        key = (app_label, model, codename)
        if key not in permissions_by_key:
            content_type = ContentType.objects.get(app_label=app_label, model=model)
            permissions_by_key[key] = Permission.objects.get(content_type=content_type, codename=codename)
        PermissionDescription.objects.get_or_create(
            permission=permissions_by_key[key], defaults={"description": description}
        )

    for manage_key, view_key in IMPLIED_VIEW_PERMISSIONS.items():
        description = PermissionDescription.objects.get(permission=permissions_by_key[manage_key])
        description.implied_view_permission = permissions_by_key[view_key]
        description.save(update_fields=["implied_view_permission"])

    group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
    group.permissions.add(*[permissions_by_key[("account", "user", codename)] for codename, _ in ACCOUNT_PERMISSIONS])
    for user in User.objects.filter(is_staff=True):
        user.groups.add(group)

    for role_name, codenames in DATASET_ROLE_PERMISSIONS.items():
        role, _ = DatasetRole.objects.get_or_create(name=role_name, defaults={"is_system": True})
        role.permissions.set([permissions_by_key[("catalog", "dataset", codename)] for codename in codenames])

    User.objects.filter(email="AnonymousUser", is_service_account=False).delete()


def remove_admin_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name=ADMIN_GROUP_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0002_user_is_service_account"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("catalog", "0015_dataset_permissions_and_roles"),
        ("agent", "0031_add_view_all_conversations_permission"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="user",
            options={"permissions": ACCOUNT_PERMISSIONS},
        ),
        migrations.CreateModel(
            name="DatasetRole",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50, unique=True)),
                ("is_system", models.BooleanField(default=False)),
                (
                    "permissions",
                    models.ManyToManyField(
                        limit_choices_to={"content_type__app_label": "catalog", "content_type__model": "dataset"},
                        to="auth.permission",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PermissionDescription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.TextField()),
                (
                    "permission",
                    models.OneToOneField(
                        on_delete=models.CASCADE,
                        related_name="description_entry",
                        to="auth.permission",
                    ),
                ),
                (
                    "implied_view_permission",
                    models.ForeignKey(
                        blank=True,
                        help_text="Set on a manage_X permission's own row when checking it should also check a "
                        "view_X permission in the composer, the single source of truth the frontend checklist reads",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="auth.permission",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="DatasetGroupRoleAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "dataset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="group_role_assignments",
                        to="catalog.dataset",
                    ),
                ),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dataset_role_assignments",
                        to="auth.group",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="group_assignments",
                        to="account.datasetrole",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("group", "dataset"), name="unique_dataset_group_role_assignment")
                ],
            },
        ),
        migrations.CreateModel(
            name="DatasetUserRoleAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "dataset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_role_assignments",
                        to="catalog.dataset",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_assignments",
                        to="account.datasetrole",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dataset_role_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("user", "dataset"), name="unique_dataset_user_role_assignment")
                ],
            },
        ),
        migrations.RunPython(create_permissions_admin_group_and_roles, remove_admin_group),
    ]
