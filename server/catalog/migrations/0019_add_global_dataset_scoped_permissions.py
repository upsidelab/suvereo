from django.db import migrations

ADMIN_GROUP_NAME = "Admin"

# (codename, name) -- the new global "_all_datasets" counterparts.
GLOBAL_PERMISSIONS = [
    ("converse_all_datasets", "Can converse with agents in every data set"),
    ("manage_all_agents", "Can manage agents in every data set"),
    ("view_all_integrations", "Can view every data set's integrations"),
    ("manage_all_integrations", "Can manage every data set's integrations"),
]

# The old bare (no per-object) grants these new global permissions supersede for Admin --
# has_dataset_perm now checks the global counterpart directly, so re-granting the old
# dataset-scoped codenames globally is no longer needed.
SUPERSEDED_CODENAMES = ["converse", "manage_agents", "view_integrations", "manage_integrations"]


def add_global_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")

    content_type, _ = ContentType.objects.get_or_create(app_label="catalog", model="dataset")
    new_permissions = []
    for codename, name in GLOBAL_PERMISSIONS:
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type, codename=codename, defaults={"name": name}
        )
        new_permissions.append(permission)

    group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
    group.permissions.add(*new_permissions)
    group.permissions.remove(*Permission.objects.filter(content_type=content_type, codename__in=SUPERSEDED_CODENAMES))


def reverse_add_global_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")

    try:
        content_type = ContentType.objects.get(app_label="catalog", model="dataset")
    except ContentType.DoesNotExist:
        return
    try:
        group = Group.objects.get(name=ADMIN_GROUP_NAME)
    except Group.DoesNotExist:
        return

    superseded = Permission.objects.filter(content_type=content_type, codename__in=SUPERSEDED_CODENAMES)
    group.permissions.add(*superseded)
    new_codenames = [codename for codename, _ in GLOBAL_PERMISSIONS]
    group.permissions.remove(*Permission.objects.filter(content_type=content_type, codename__in=new_codenames))


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0018_add_integration_permissions"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="dataset",
            options={
                "default_permissions": ("add", "change", "delete"),
                "permissions": [
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
                ],
            },
        ),
        migrations.RunPython(add_global_permissions, reverse_add_global_permissions),
    ]
