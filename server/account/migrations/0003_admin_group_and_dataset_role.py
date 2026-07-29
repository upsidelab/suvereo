from django.db import migrations, models

ADMIN_GROUP_NAME = "Admin"

# (app_label, model, codename, human-readable name)
PERMISSIONS = [
    ("account", "user", "manage_users", "Can manage human users"),
    ("account", "user", "manage_service_accounts", "Can manage service accounts"),
    ("catalog", "dataset", "manage_datasets", "Can manage data sets"),
    ("catalog", "dataset", "access_all_datasets", "Can access all data sets"),
    ("catalog", "dataset", "configure_models", "Can read model provider configuration"),
]


def create_admin_group(apps, schema_editor):
    """Create the Admin group, its permissions, and migrate is_staff users into it.

    Permissions are created explicitly via ContentType because the post_migrate
    signal that materializes Meta.permissions has not run yet within the same
    migrate invocation.
    """
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    User = apps.get_model("account", "User")

    group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
    permissions = []
    for app_label, model, codename, name in PERMISSIONS:
        content_type, _ = ContentType.objects.get_or_create(app_label=app_label, model=model)
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type, codename=codename, defaults={"name": name}
        )
        permissions.append(permission)
    group.permissions.set(permissions)

    for user in User.objects.filter(is_staff=True):
        user.groups.add(group)


def remove_admin_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name=ADMIN_GROUP_NAME).delete()


def delete_anonymous_user_row(apps, schema_editor):
    """Remove the real User row guardian's post_migrate hook used to create.

    Now that ANONYMOUS_USER_NAME is set to None, guardian no longer creates or
    uses this row, but any dev/staging database that ran migrations before that
    change may still have it lying around, reachable via /api/users.
    """
    User = apps.get_model("account", "User")
    User.objects.filter(email="AnonymousUser", is_service_account=False).delete()


def seed_dataset_roles(apps, schema_editor):
    """Seed the viewer/editor DatasetRole rows so existing role-name strings keep working.

    Permissions are fetched via get_or_create (not a plain .get()) because Meta.permissions
    are only materialized by the post_migrate signal after this entire migrate invocation
    finishes — mirrors catalog's own handling of catalog.manage_agents/access_dataset.
    """
    DatasetRole = apps.get_model("account", "DatasetRole")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type, _ = ContentType.objects.get_or_create(app_label="catalog", model="dataset")
    access_dataset, _ = Permission.objects.get_or_create(
        content_type=content_type, codename="access_dataset", defaults={"name": "Can access this data set"}
    )
    manage_agents, _ = Permission.objects.get_or_create(
        content_type=content_type, codename="manage_agents", defaults={"name": "Can manage agents in this data set"}
    )

    viewer, _ = DatasetRole.objects.get_or_create(name="viewer", defaults={"is_system": True})
    viewer.permissions.set([access_dataset])

    editor, _ = DatasetRole.objects.get_or_create(name="editor", defaults={"is_system": True})
    editor.permissions.set([access_dataset, manage_agents])


def reverse_noop(apps, schema_editor):
    """No-op: reversing the DatasetRole creation drops its table right after via CreateModel's
    reversal, so deleting rows here first is both redundant and actively harmful — it cascades
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
                    ("manage_service_accounts", "Can manage service accounts"),
                ]
            },
        ),
        migrations.RunPython(create_admin_group, remove_admin_group),
        migrations.RunPython(delete_anonymous_user_row, reverse_noop),
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
        migrations.RunPython(seed_dataset_roles, reverse_noop),
    ]
