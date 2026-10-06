from django.db import migrations


def delete_sessions_content_type(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="sessions").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0013_dataset_role_name_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunSQL("DROP TABLE IF EXISTS django_session", reverse_sql=migrations.RunSQL.noop),
        migrations.RunPython(delete_sessions_content_type, migrations.RunPython.noop),
    ]
