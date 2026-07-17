from django.db import migrations

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


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0003_alter_user_options"),
        ("catalog", "0015_alter_dataset_options"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(create_admin_group, remove_admin_group)]
