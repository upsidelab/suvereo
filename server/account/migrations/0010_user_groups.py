import django.db.models.deletion
from django.apps import apps as installed_apps
from django.conf import settings
from django.contrib.auth.management import create_permissions
from django.db import migrations, models

# `assign_usergroup` comes from `UserGroup.Meta.permissions` and the other four from `post_migrate`;
# this only gives them the names the vocabulary publishes, the way 0007 names the rest of it.
PERMISSION_NAMES = {
    "account.view_usergroup": "See groups and the roles they hold",
    "account.add_usergroup": "Create groups",
    "account.change_usergroup": "Edit a group's name",
    "account.delete_usergroup": "Delete groups, giving up the roles they hold",
    "account.assign_usergroup": "Add users to and remove them from groups",
}


def set_permission_names(apps, schema_editor):
    create_permissions(installed_apps.get_app_config("account"), verbosity=0)

    permission_model = apps.get_model("auth", "Permission")
    for code, name in PERMISSION_NAMES.items():
        app_label, codename = code.split(".")
        permission_model.objects.filter(content_type__app_label=app_label, codename=codename).update(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0009_role_lifecycle_permissions"),
        ("catalog", "0016_integration_sync_permission"),
        ("auth", "0012_alter_user_first_name_max_length"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, unique=True)),
                ("global_roles", models.ManyToManyField(blank=True, related_name="holders", to="account.globalrole")),
                (
                    "members",
                    models.ManyToManyField(blank=True, related_name="user_groups", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "permissions": [("assign_usergroup", "Add users to and remove them from groups")],
            },
        ),
        migrations.CreateModel(
            name="DatasetGroupRoleAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dataset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="catalog.dataset")),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="account.datasetrole")),
                ("group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="account.usergroup")),
            ],
            options={
                "unique_together": {("group", "dataset", "role")},
            },
        ),
        migrations.RunPython(set_permission_names, migrations.RunPython.noop),
    ]
