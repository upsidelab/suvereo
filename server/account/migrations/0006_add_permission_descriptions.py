import django.db.models.deletion
from django.db import migrations, models

DESCRIPTIONS = [
    ("account", "user", "manage_users", "Can create, edit, and delete user accounts, and change their roles."),
    ("account", "user", "view_users", "Can see the list of users and their roles, without editing."),
    (
        "account",
        "user",
        "manage_service_accounts",
        "Can create, edit, and delete service (API) accounts and their tokens.",
    ),
    ("account", "user", "view_service_accounts", "Can see the list of service accounts, without editing."),
    ("catalog", "dataset", "manage_datasets", "Can create, configure, and delete data sets."),
    (
        "catalog",
        "dataset",
        "view_all_datasets",
        "Can see every data set in the system, regardless of per-dataset role assignments.",
    ),
    (
        "catalog",
        "dataset",
        "configure_models",
        "Can view the configuration of language model providers (e.g. provider keys/parameters).",
    ),
    (
        "catalog",
        "dataset",
        "view_dataset",
        "Can browse this data set's catalog (products, documents) -- does not include chatting with its agents.",
    ),
    ("catalog", "dataset", "converse", "Can chat with this data set's agents and see their own message history."),
    ("catalog", "dataset", "manage_agents", "Can create, configure, and delete this data set's agents."),
    ("catalog", "dataset", "view_integrations", "Can see this data set's configured e-commerce integrations."),
    (
        "catalog",
        "dataset",
        "manage_integrations",
        "Can add, edit, delete, and sync this data set's e-commerce integrations.",
    ),
    (
        "agent",
        "conversation",
        "view_all_conversations",
        "Can read (view-only) every user's conversations across every data set -- not just their own.",
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
    PermissionDescription = apps.get_model("account", "PermissionDescription")
    PermissionDescription.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0005_reseed_dataset_roles"),
        ("catalog", "0018_add_integration_permissions"),
        ("agent", "0033_add_view_all_conversations_permission"),
    ]

    operations = [
        migrations.CreateModel(
            name="PermissionDescription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.TextField()),
                (
                    "permission",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="description_entry",
                        to="auth.permission",
                    ),
                ),
            ],
        ),
        migrations.RunPython(seed_permission_descriptions, reverse_seed_permission_descriptions),
    ]
