from django.db import migrations, models

ADMIN_GROUP_NAME = "Admin"

# account.user permissions Admin holds globally.
ADMIN_ACCOUNT_PERMISSIONS = [
    ("manage_users", "Can manage human users"),
    ("view_users", "Can view human users"),
    ("manage_service_accounts", "Can manage service accounts"),
    ("view_service_accounts", "Can view service accounts"),
]

# catalog.dataset permissions the seeded viewer/editor DatasetRoles reference, created here via
# get_or_create so this doesn't need to depend on catalog's own permission-creation migration --
# whichever migration runs first creates the row, the other just finds it already there.
DATASET_ROLE_PERMISSIONS = {
    "view_dataset": "Can view this data set",
    "converse": "Can converse with this data set's agents",
    "manage_agents": "Can manage agents in this data set",
    "view_integrations": "Can view this data set's integrations",
    "manage_integrations": "Can manage this data set's integrations",
}
VIEWER_CODENAMES = ["view_dataset", "converse"]
EDITOR_CODENAMES = ["view_dataset", "converse", "manage_agents", "view_integrations", "manage_integrations"]


def create_admin_group_and_dataset_roles(apps, schema_editor):
    """Create the Admin group with its account-level permissions, migrate any pre-existing
    is_staff users into it, and seed the viewer/editor DatasetRole presets.

    Permissions are created explicitly via ContentType because the post_migrate signal that
    materializes Meta.permissions has not run yet within the same migrate invocation.
    """
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    User = apps.get_model("account", "User")
    DatasetRole = apps.get_model("account", "DatasetRole")

    user_content_type, _ = ContentType.objects.get_or_create(app_label="account", model="user")
    admin_permissions = []
    for codename, name in ADMIN_ACCOUNT_PERMISSIONS:
        permission, _ = Permission.objects.get_or_create(
            content_type=user_content_type, codename=codename, defaults={"name": name}
        )
        admin_permissions.append(permission)

    group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
    group.permissions.add(*admin_permissions)

    for user in User.objects.filter(is_staff=True):
        user.groups.add(group)

    dataset_content_type, _ = ContentType.objects.get_or_create(app_label="catalog", model="dataset")
    dataset_permissions = {}
    for codename, name in DATASET_ROLE_PERMISSIONS.items():
        permission, _ = Permission.objects.get_or_create(
            content_type=dataset_content_type, codename=codename, defaults={"name": name}
        )
        dataset_permissions[codename] = permission

    viewer, _ = DatasetRole.objects.get_or_create(name="viewer", defaults={"is_system": True})
    viewer.permissions.set([dataset_permissions[codename] for codename in VIEWER_CODENAMES])

    editor, _ = DatasetRole.objects.get_or_create(name="editor", defaults={"is_system": True})
    editor.permissions.set([dataset_permissions[codename] for codename in EDITOR_CODENAMES])


def remove_admin_group_and_dataset_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name=ADMIN_GROUP_NAME).delete()
    # DatasetRole rows are dropped by this migration's own CreateModel reversal.


def delete_anonymous_user_row(apps, schema_editor):
    """Remove the real User row guardian's post_migrate hook used to create.

    Now that ANONYMOUS_USER_NAME is set to None, guardian no longer creates or
    uses this row, but any dev/staging database that ran migrations before that
    change may still have it lying around, reachable via /api/users.
    """
    User = apps.get_model("account", "User")
    User.objects.filter(email="AnonymousUser", is_service_account=False).delete()


def reverse_noop(apps, schema_editor):
    """No-op: reversing DatasetRole creation drops its table right after via CreateModel's
    reversal, so deleting rows here first is both redundant and actively harmful -- it cascades
    into the permissions M2M through-table, leaving pending trigger events that make Postgres
    refuse the subsequent DROP TABLE in the same transaction.
    """


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0002_user_is_service_account"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="user",
            options={
                "permissions": [
                    ("manage_users", "Can manage human users"),
                    ("view_users", "Can view human users"),
                    ("manage_service_accounts", "Can manage service accounts"),
                    ("view_service_accounts", "Can view service accounts"),
                ]
            },
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
        migrations.RunPython(create_admin_group_and_dataset_roles, remove_admin_group_and_dataset_roles),
        migrations.RunPython(delete_anonymous_user_row, reverse_noop),
    ]
