from django.apps import apps as installed_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

# A global role no longer holds anything on a data set, so what 0009 named this is now false.
PERMISSION_NAMES = {
    "account.delete_globalrole": "Delete global roles, revoking them from everyone holding them",
}


def set_permission_names(apps, schema_editor):
    create_permissions(installed_apps.get_app_config("account"), verbosity=0)

    permission_model = apps.get_model("auth", "Permission")
    for code, name in PERMISSION_NAMES.items():
        app_label, codename = code.split(".")
        permission_model.objects.filter(content_type__app_label=app_label, codename=codename).update(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0010_user_groups"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.DeleteModel(name="DatasetGlobalRoleAssignment"),
        migrations.RunPython(set_permission_names, migrations.RunPython.noop),
    ]
