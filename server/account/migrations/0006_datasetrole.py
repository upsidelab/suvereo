from django.db import migrations, models


def seed_dataset_roles(apps, schema_editor):
    """Seed the viewer/editor DatasetRole rows so existing role-name strings keep working.

    Permissions are fetched via get_or_create (not a plain .get()) because Meta.permissions
    are only materialized by the post_migrate signal after this entire migrate invocation
    finishes — mirrors 0018/0019's handling of catalog.manage_agents/access_dataset.
    """
    DatasetRole = apps.get_model("account", "DatasetRole")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type, _ = ContentType.objects.get_or_create(app_label="catalog", model="dataset")
    access_dataset, _ = Permission.objects.get_or_create(
        content_type=content_type, codename="access_dataset", defaults={"name": "Can access this data set"}
    )
    manage_agents, _ = Permission.objects.get_or_create(
        content_type=content_type, codename="manage_agents", defaults={"name": "Can manage agents in this data set"}
    )

    viewer, _ = DatasetRole.objects.get_or_create(name="viewer", defaults={"is_system": True})
    viewer.permissions.set([access_dataset])

    editor, _ = DatasetRole.objects.get_or_create(name="editor", defaults={"is_system": True})
    editor.permissions.set([access_dataset, manage_agents])


def reverse_noop(apps, schema_editor):
    """No-op: reversing this migration drops the DatasetRole table right after via CreateModel's
    reversal, so deleting rows here first is both redundant and actively harmful — it cascades
    into the permissions M2M through-table, leaving pending trigger events that make Postgres
    refuse the subsequent DROP TABLE in the same transaction. Mirrors 0019's reverse_noop.
    """


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0005_delete_anonymous_user_row"),
        # Deliberately the migration that first declares both access_dataset and manage_agents
        # in DataSet.Meta.permissions (0017), not catalog's current tip (0020). Depending on a
        # later catalog migration would make this migration get swept into any test/tooling that
        # reverses catalog past 0018-0020 (see catalog/tests/test_migration_0019.py), which then
        # hits a Postgres "pending trigger events" error unwinding this migration's RunPython
        # delete immediately followed by its CreateModel's DROP TABLE in the same transaction.
        ("catalog", "0017_alter_dataset_options"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="DatasetRole",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50, unique=True)),
                ("is_system", models.BooleanField(default=False)),
                (
                    "permissions",
                    models.ManyToManyField(
                        limit_choices_to={"content_type__app_label": "catalog", "content_type__model": "dataset"},
                        to="auth.permission",
                    ),
                ),
            ],
        ),
        migrations.RunPython(seed_dataset_roles, reverse_noop),
    ]
