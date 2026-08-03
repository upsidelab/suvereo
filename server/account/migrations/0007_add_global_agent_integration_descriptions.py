from django.db import migrations

# Seeds PermissionDescription rows for the global "_all_datasets" counterparts added in
# catalog/migrations/0019_add_global_dataset_scoped_permissions.py. Follows the same
# strict-get pattern (not get_or_create) as account/0006 -- see that migration's own
# comment for why: Migration.dependencies below must list whatever migration created each
# permission, or Permission.objects.get(...) raises DoesNotExist on a fresh database.

DESCRIPTIONS = [
    (
        "catalog",
        "dataset",
        "converse_all_datasets",
        "Can chat with every data set's agents and see their own message history.",
    ),
    ("catalog", "dataset", "manage_all_agents", "Can create, configure, and delete agents in every data set."),
    (
        "catalog",
        "dataset",
        "view_all_integrations",
        "Can see every data set's configured e-commerce integrations.",
    ),
    (
        "catalog",
        "dataset",
        "manage_all_integrations",
        "Can add, edit, delete, and sync e-commerce integrations in every data set.",
    ),
]


def seed_permission_descriptions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    PermissionDescription = apps.get_model("account", "PermissionDescription")

    for app_label, model, codename, description in DESCRIPTIONS:
        content_type = ContentType.objects.get(app_label=app_label, model=model)
        permission = Permission.objects.get(content_type=content_type, codename=codename)
        PermissionDescription.objects.get_or_create(permission=permission, defaults={"description": description})


def reverse_seed_permission_descriptions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    PermissionDescription = apps.get_model("account", "PermissionDescription")

    codenames = [codename for _, _, codename, _ in DESCRIPTIONS]
    content_type = ContentType.objects.get(app_label="catalog", model="dataset")
    PermissionDescription.objects.filter(
        permission__content_type=content_type, permission__codename__in=codenames
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0006_add_permission_descriptions"),
        ("catalog", "0019_add_global_dataset_scoped_permissions"),
    ]

    operations = [migrations.RunPython(seed_permission_descriptions, reverse_seed_permission_descriptions)]
