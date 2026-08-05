from django.db import migrations

ADMIN_GROUP_NAME = "Admin"

# Every catalog.dataset permission, final state. The dataset-scoped ones (view_dataset,
# manage_agents, converse, view_integrations, manage_integrations) are granted per-object via a
# DatasetRole (see account.0003) rather than to Admin directly. Admin instead holds each one's
# global "_all_datasets" counterpart, checked by account.authorization.has_dataset_perm.
PERMISSIONS = [
    ("manage_datasets", "Can manage data sets"),
    ("view_all_datasets", "Can view all data sets"),
    ("configure_models", "Can read model provider configuration"),
    ("view_dataset", "Can view this data set"),
    ("manage_agents", "Can manage agents in this data set"),
    ("converse", "Can converse with this data set's agents"),
    ("view_integrations", "Can view this data set's integrations"),
    ("manage_integrations", "Can manage this data set's integrations"),
    ("converse_all_datasets", "Can converse with agents in every data set"),
    ("manage_all_agents", "Can manage agents in every data set"),
    ("view_all_integrations", "Can view every data set's integrations"),
    ("manage_all_integrations", "Can manage every data set's integrations"),
]

ADMIN_GLOBAL_CODENAMES = [
    "manage_datasets",
    "view_all_datasets",
    "configure_models",
    "converse_all_datasets",
    "manage_all_agents",
    "view_all_integrations",
    "manage_all_integrations",
]


def create_dataset_permissions_and_grant_admin(apps, schema_editor):
    """Create every catalog.dataset permission explicitly and grant Admin the global ones.

    Permissions are created via ContentType/get_or_create because the post_migrate signal that
    materializes Meta.permissions has not run yet within the same migrate invocation. Uses
    group.permissions.add() rather than .set() so this doesn't need to run in any particular
    order relative to account's migration, which grants Admin its own, separate set of
    permissions the same way.
    """
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type, _ = ContentType.objects.get_or_create(app_label="catalog", model="dataset")
    permissions_by_codename = {}
    for codename, name in PERMISSIONS:
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type, codename=codename, defaults={"name": name}
        )
        permissions_by_codename[codename] = permission

    group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
    group.permissions.add(*[permissions_by_codename[codename] for codename in ADMIN_GLOBAL_CODENAMES])


def remove_dataset_permissions_and_grant_admin(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    try:
        group = Group.objects.get(name=ADMIN_GROUP_NAME)
    except Group.DoesNotExist:
        return
    group.permissions.remove(
        *Permission.objects.filter(content_type__app_label="catalog", codename__in=ADMIN_GLOBAL_CODENAMES)
    )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0014_drop_domain_tables_add_integration"),
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
                "permissions": PERMISSIONS,
            },
        ),
        migrations.RemoveField(
            model_name="dataset",
            name="users",
        ),
        migrations.RunPython(create_dataset_permissions_and_grant_admin, remove_dataset_permissions_and_grant_admin),
    ]
