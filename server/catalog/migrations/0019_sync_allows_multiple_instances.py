from django.db import migrations, models


def sync_allows_multiple_instances(apps, schema_editor):
    # The flag is copied from the plugin when an integration is created. ALLOWS_MULTIPLE_INSTANCES
    # now defaults to True, so existing rows are re-read from their plugins. Rows whose type has no
    # registered plugin are left as they are.
    from catalog.integrations.registry import IntegrationPluginRegistry

    Integration = apps.get_model("catalog", "Integration")
    for plugin_class in IntegrationPluginRegistry().get_plugin_classes():
        Integration.objects.filter(type=plugin_class.TYPE).update(
            allows_multiple_instances=plugin_class.ALLOWS_MULTIPLE_INSTANCES
        )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0018_dataset_is_temporary"),
    ]

    operations = [
        migrations.AlterField(
            model_name="integration",
            name="allows_multiple_instances",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(sync_allows_multiple_instances, migrations.RunPython.noop),
    ]
