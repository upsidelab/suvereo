import django.db.models.deletion
from django.apps import apps as installed_apps
from django.conf import settings
from django.contrib.auth.management import create_permissions
from django.db import migrations, models

# Global roles moved off `auth.Group`, so their codes are new rows. Named the way 0007 names the
# rest of the vocabulary; `auth.view_group` and `account.assign_group` left 0007 with the meaning.
PERMISSION_NAMES = {
    "account.view_globalrole": "See global roles and the permissions they carry",
    "account.assign_globalrole": "Add users to and remove them from global roles",
}


def set_permission_names(apps, schema_editor):
    create_permissions(installed_apps.get_app_config("account"), verbosity=0)

    permission_model = apps.get_model("auth", "Permission")
    for code, name in PERMISSION_NAMES.items():
        app_label, codename = code.split(".")
        permission_model.objects.filter(content_type__app_label=app_label, codename=codename).update(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0007_permission_names"),
        ("auth", "0012_alter_user_first_name_max_length"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GlobalRole",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, unique=True)),
                (
                    "members",
                    models.ManyToManyField(blank=True, related_name="global_roles", to=settings.AUTH_USER_MODEL),
                ),
                ("permissions", models.ManyToManyField(blank=True, to="auth.permission")),
            ],
            options={
                "permissions": [("assign_globalrole", "Add users to and remove them from global roles")],
            },
        ),
        migrations.AlterField(
            model_name="datasetglobalroleassignment",
            name="global_role",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="account.globalrole"),
        ),
        migrations.AlterModelOptions(
            name="user",
            options={
                "permissions": [
                    ("add_serviceaccount", "Can add service account"),
                    ("change_serviceaccount", "Can change service account"),
                    ("view_serviceaccount", "Can view service account"),
                ],
                "verbose_name": "user",
                "verbose_name_plural": "users",
            },
        ),
        migrations.RunPython(set_permission_names, migrations.RunPython.noop),
    ]
