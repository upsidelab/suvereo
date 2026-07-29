from django.db import migrations

ADMIN_GROUP_NAME = "Admin"
MANAGE_AGENTS_CODENAME = "manage_agents"
MANAGE_AGENTS_NAME = "Can manage agents in this data set"


def grant_manage_agents(apps, schema_editor):
    """Create catalog.manage_agents explicitly and grant it to the Admin group.

    manage_agents lives on DataSet (not Agent) so it can be granted per-object
    via guardian without crossing content-type boundaries. The permission is
    created via ContentType because the post_migrate signal that materializes
    Meta.permissions has not run yet within the same migrate invocation.

    Uses .add() rather than .set() deliberately: this must run after account's
    admin-group-creation migration (which does group.permissions.set(...) with
    the base five permissions) without wiping those out.
    """
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type, _ = ContentType.objects.get_or_create(app_label="catalog", model="dataset")
    permission, _ = Permission.objects.get_or_create(
        content_type=content_type, codename=MANAGE_AGENTS_CODENAME, defaults={"name": MANAGE_AGENTS_NAME}
    )
    group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
    group.permissions.add(permission)


def revoke_manage_agents(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    try:
        group = Group.objects.get(name=ADMIN_GROUP_NAME)
    except Group.DoesNotExist:
        return
    group.permissions.remove(
        *Permission.objects.filter(codename=MANAGE_AGENTS_CODENAME, content_type__app_label="catalog")
    )


def migrate_users_to_editor_grants(apps, schema_editor):
    """Backfill every existing DataSet.users row as an editor grant via guardian.

    Runs before the schema operation below that drops the users M2M, so the field
    is still queryable here through the historical DataSet model. guardian's
    assign_perm does an isinstance() check against the live get_user_model()
    internally, which historical User instances from apps.get_model() never
    satisfy — so the target user is re-fetched through the concrete model.

    catalog.access_dataset is created explicitly via ContentType here because
    Meta.permissions are only materialized by the post_migrate signal after this
    entire migrate invocation finishes — the Permission row does not exist yet
    at this point in a one-shot migrate of a fresh or lagging database.
    """
    from guardian.shortcuts import assign_perm

    from account.models import User

    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    DataSet = apps.get_model("catalog", "DataSet")

    content_type, _ = ContentType.objects.get_or_create(app_label="catalog", model="dataset")
    Permission.objects.get_or_create(
        content_type=content_type, codename="access_dataset", defaults={"name": "Can access this data set"}
    )

    for dataset in DataSet.objects.prefetch_related("users").all():
        for user_pk in dataset.users.values_list("pk", flat=True):
            user = User.objects.get(pk=user_pk)
            assign_perm("catalog.access_dataset", user, dataset)
            assign_perm("catalog.manage_agents", user, dataset)


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0014_drop_domain_tables_add_integration"),
        ("guardian", "0001_initial"),
        # Must run after account's admin-group-creation migration: grant_manage_agents
        # above uses .add() specifically to avoid clobbering the base permission set
        # that migration assigns via .set().
        ("account", "0003_admin_group_and_dataset_role"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="dataset",
            options={
                "permissions": [
                    ("manage_datasets", "Can manage data sets"),
                    ("access_all_datasets", "Can access all data sets"),
                    ("configure_models", "Can read model provider configuration"),
                    ("access_dataset", "Can access this data set"),
                    ("manage_agents", "Can manage agents in this data set"),
                ]
            },
        ),
        migrations.RunPython(grant_manage_agents, revoke_manage_agents),
        migrations.RunPython(migrate_users_to_editor_grants, reverse_noop),
        migrations.RemoveField(
            model_name="dataset",
            name="users",
        ),
    ]
