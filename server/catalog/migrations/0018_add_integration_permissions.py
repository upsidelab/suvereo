from django.db import migrations

ADMIN_GROUP_NAME = "Admin"
PERMISSIONS = [
    ("view_integrations", "Can view this data set's integrations"),
    ("manage_integrations", "Can manage this data set's integrations"),
]


def add_integration_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")

    content_type, _ = ContentType.objects.get_or_create(app_label="catalog", model="dataset")
    permissions = []
    for codename, name in PERMISSIONS:
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type, codename=codename, defaults={"name": name}
        )
        permissions.append(permission)
    group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
    group.permissions.add(*permissions)


def remove_integration_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    try:
        group = Group.objects.get(name=ADMIN_GROUP_NAME)
    except Group.DoesNotExist:
        return
    codenames = [codename for codename, _ in PERMISSIONS]
    group.permissions.remove(*Permission.objects.filter(codename__in=codenames, content_type__app_label="catalog"))


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0017_add_converse_permission"),
        ("account", "0003_admin_group_and_dataset_role"),
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
                ]
            },
        ),
        migrations.RunPython(add_integration_permissions, remove_integration_permissions),
    ]
