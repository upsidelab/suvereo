from django.db import migrations

VIEWER_CODENAMES = ["view_dataset", "converse"]
EDITOR_CODENAMES = ["view_dataset", "converse", "manage_agents", "view_integrations", "manage_integrations"]


def reseed_dataset_roles(apps, schema_editor):
    DatasetRole = apps.get_model("account", "DatasetRole")
    Permission = apps.get_model("auth", "Permission")

    viewer = DatasetRole.objects.get(name="viewer")
    viewer.permissions.set(Permission.objects.filter(content_type__app_label="catalog", codename__in=VIEWER_CODENAMES))

    editor = DatasetRole.objects.get(name="editor")
    editor.permissions.set(Permission.objects.filter(content_type__app_label="catalog", codename__in=EDITOR_CODENAMES))


def reverse_reseed_dataset_roles(apps, schema_editor):
    DatasetRole = apps.get_model("account", "DatasetRole")
    Permission = apps.get_model("auth", "Permission")

    viewer = DatasetRole.objects.get(name="viewer")
    viewer.permissions.set(Permission.objects.filter(content_type__app_label="catalog", codename="view_dataset"))

    editor = DatasetRole.objects.get(name="editor")
    editor.permissions.set(
        Permission.objects.filter(content_type__app_label="catalog", codename__in=["view_dataset", "manage_agents"])
    )


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0004_add_view_permissions"),
        ("catalog", "0018_add_integration_permissions"),
    ]

    operations = [migrations.RunPython(reseed_dataset_roles, reverse_reseed_dataset_roles)]
