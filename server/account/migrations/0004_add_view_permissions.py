from django.db import migrations

ADMIN_GROUP_NAME = "Admin"
PERMISSIONS = [
    ("view_users", "Can view human users"),
    ("view_service_accounts", "Can view service accounts"),
]


def add_view_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")

    content_type, _ = ContentType.objects.get_or_create(app_label="account", model="user")
    permissions = []
    for codename, name in PERMISSIONS:
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type, codename=codename, defaults={"name": name}
        )
        permissions.append(permission)
    group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
    group.permissions.add(*permissions)


def remove_view_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    try:
        group = Group.objects.get(name=ADMIN_GROUP_NAME)
    except Group.DoesNotExist:
        return
    codenames = [codename for codename, _ in PERMISSIONS]
    group.permissions.remove(*Permission.objects.filter(codename__in=codenames, content_type__app_label="account"))


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0003_admin_group_and_dataset_role"),
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
        migrations.RunPython(add_view_permissions, remove_view_permissions),
    ]
