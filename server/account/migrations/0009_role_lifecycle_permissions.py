from django.apps import apps as installed_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

# Django auto-creates `add`/`change`/`delete` for every model - so this migration
# only gives them the names the vocabulary publishes, the way 0007 names the rest of it.
PERMISSION_NAMES = {
    "account.add_globalrole": "Create global roles",
    "account.change_globalrole": "Edit a global role's name and the permissions it carries",
    "account.delete_globalrole": "Delete global roles, giving up the roles they hold on data sets",
    "account.add_datasetrole": "Create dataset roles",
    "account.change_datasetrole": "Edit a dataset role's name and the permissions it carries",
    "account.delete_datasetrole": "Delete dataset roles, revoking them from everyone holding them",
}


def set_permission_names(apps, schema_editor):
    create_permissions(installed_apps.get_app_config("account"), verbosity=0)

    permission_model = apps.get_model("auth", "Permission")
    for code, name in PERMISSION_NAMES.items():
        app_label, codename = code.split(".")
        permission_model.objects.filter(content_type__app_label=app_label, codename=codename).update(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0008_global_role_model"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(set_permission_names, migrations.RunPython.noop)]
