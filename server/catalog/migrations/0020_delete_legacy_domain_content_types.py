from django.db import migrations

# Models dropped by 0014_drop_domain_tables_add_integration. Databases upgraded from Enthusiast 1.7
# still hold their content types, and with them their permissions; fresh ones don't.
LEGACY_DOMAIN_MODELS = (
    "product",
    "productcontentchunk",
    "productsource",
    "document",
    "documentchunk",
    "documentsource",
    "ecommerceintegration",
)


def delete_legacy_domain_content_types(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="catalog", model__in=LEGACY_DOMAIN_MODELS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0019_sync_allows_multiple_instances"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(delete_legacy_domain_content_types, migrations.RunPython.noop),
    ]
