from django.db import migrations


def migrate_users_to_editor_grants(apps, schema_editor):
    """Backfill every existing DataSet.users row as an editor grant via guardian.

    Runs before the schema migration that drops the users M2M, so the field
    is still queryable here through the historical DataSet model. guardian's
    assign_perm does an isinstance() check against the live get_user_model()
    internally, which historical User instances from apps.get_model() never
    satisfy — so the target user is re-fetched through the concrete model.
    """
    from guardian.shortcuts import assign_perm

    from account.models import User

    DataSet = apps.get_model("catalog", "DataSet")
    for dataset in DataSet.objects.prefetch_related("users").all():
        for user_pk in dataset.users.values_list("pk", flat=True):
            user = User.objects.get(pk=user_pk)
            assign_perm("catalog.access_dataset", user, dataset)
            assign_perm("catalog.manage_agents", user, dataset)


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0018_grant_manage_agents_to_admin_group"),
    ]

    operations = [migrations.RunPython(migrate_users_to_editor_grants, reverse_noop)]
