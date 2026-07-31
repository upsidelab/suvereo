from django.db import migrations

ADMIN_GROUP_NAME = "Admin"
CODENAME = "converse"
NAME = "Can converse with this data set's agents"


def add_converse_permission(apps, schema_editor):
    """Create catalog.converse and grant it to the Admin group directly (a plain global
    Group.permissions grant, not a per-dataset guardian grant) -- the same mechanism
    manage_agents already uses for Admin. has_dataset_perm's first branch
    (user.has_perm(codename), no object) already returns True for any Admin-group member
    regardless of which dataset is being checked, so no additional "view_all_datasets as a
    converse bypass" logic is needed anywhere.

    converse is deliberately NOT added to GLOBAL_PERMISSION_CODENAMES (the global-scope
    composer checklist) -- it can only be composed into a dataset-scoped role via the UI,
    even though this migration grants it to Admin globally.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")

    content_type, _ = ContentType.objects.get_or_create(app_label="catalog", model="dataset")
    permission, _ = Permission.objects.get_or_create(
        content_type=content_type, codename=CODENAME, defaults={"name": NAME}
    )
    group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
    group.permissions.add(permission)


def remove_converse_permission(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    try:
        group = Group.objects.get(name=ADMIN_GROUP_NAME)
    except Group.DoesNotExist:
        return
    group.permissions.remove(*Permission.objects.filter(codename=CODENAME, content_type__app_label="catalog"))


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0016_rename_dataset_access_permissions"),
        ("account", "0003_admin_group_and_dataset_role"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="dataset",
            options={
                "db_table_comment": (
                    "List of various data sets. One data set may be the whole company's content such as blog "
                    "posts, or some part of it: a data set may be represent a brand or department."
                ),
                "default_permissions": ("add", "change", "delete"),
                "permissions": [
                    ("manage_datasets", "Can manage data sets"),
                    ("view_all_datasets", "Can view all data sets"),
                    ("configure_models", "Can read model provider configuration"),
                    ("view_dataset", "Can view this data set"),
                    ("manage_agents", "Can manage agents in this data set"),
                    ("converse", "Can converse with this data set's agents"),
                ],
            },
        ),
        migrations.RunPython(add_converse_permission, remove_converse_permission),
    ]
