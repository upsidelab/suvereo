from django.db import migrations

# django.contrib.admin and django.contrib.sessions are not installed. Databases upgraded from
# Enthusiast 1.7 still carry the admin log table and both apps' migration records; fresh ones don't.


def delete_admin_content_types(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="admin").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0015_user_is_internal"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunSQL("DROP TABLE IF EXISTS django_admin_log", reverse_sql=migrations.RunSQL.noop),
        migrations.RunPython(delete_admin_content_types, migrations.RunPython.noop),
        migrations.RunSQL(
            "DELETE FROM django_migrations WHERE app IN ('admin', 'sessions')", reverse_sql=migrations.RunSQL.noop
        ),
    ]
