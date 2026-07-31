from django.db import migrations


def backfill_dataset_role_grants(apps, schema_editor):
    """Upgrade pre-existing per-object dataset grants to the reseeded viewer/editor shapes.

    `assign_dataset_role()` is a snapshot operation: it copies a DatasetRole's permissions
    into individual guardian per-object grants at assignment time, with no live link back to
    the role afterward. The 0005 migration reseeded the *template* role rows, but every grant
    created before this branch still holds the old permission set. This migration brings those
    existing grants up to date so nobody loses access on migration day:

    - every (holder, dataset) pair holding `view_dataset` also gets `converse` (both old role
      shapes lacked it, and `ConversationView`/`ConversationListView` now require it);
    - a pair is treated as "editor-tier" only if it ALSO already holds `manage_agents` for
      that same dataset (the old editor shape granted `view_dataset` + `manage_agents`; the
      old viewer shape granted `view_dataset` alone). Only editor-tier pairs additionally get
      `view_integrations` and `manage_integrations` — granting those to every `view_dataset`
      holder indiscriminately would resurrect the exact information-disclosure bug fixed by
      restricting integration reads to `view_integrations`.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    UserObjectPermission = apps.get_model("guardian", "UserObjectPermission")
    GroupObjectPermission = apps.get_model("guardian", "GroupObjectPermission")
    DataSet = apps.get_model("catalog", "DataSet")

    dataset_ct = ContentType.objects.get_for_model(DataSet)
    perms = {
        p.codename: p
        for p in Permission.objects.filter(
            content_type=dataset_ct,
            codename__in=["view_dataset", "manage_agents", "converse", "view_integrations", "manage_integrations"],
        )
    }

    for model, holder_field in [(UserObjectPermission, "user_id"), (GroupObjectPermission, "group_id")]:
        view_pairs = set(
            model.objects.filter(content_type=dataset_ct, permission=perms["view_dataset"]).values_list(
                holder_field, "object_pk"
            )
        )
        manage_agents_pairs = set(
            model.objects.filter(content_type=dataset_ct, permission=perms["manage_agents"]).values_list(
                holder_field, "object_pk"
            )
        )

        for holder_id, object_pk in view_pairs:
            model.objects.get_or_create(
                content_type=dataset_ct,
                permission=perms["converse"],
                object_pk=object_pk,
                **{holder_field: holder_id},
            )
            if (holder_id, object_pk) in manage_agents_pairs:
                for codename in ("view_integrations", "manage_integrations"):
                    model.objects.get_or_create(
                        content_type=dataset_ct,
                        permission=perms[codename],
                        object_pk=object_pk,
                        **{holder_field: holder_id},
                    )


def reverse_backfill_dataset_role_grants(apps, schema_editor):
    """No-op: this backfill is not cleanly reversible.

    There is no way to distinguish a grant this migration added from one that already
    existed or was created independently afterward, so attempting to remove grants on
    reverse would risk revoking access that has nothing to do with this migration.
    """
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0005_reseed_dataset_roles"),
    ]

    operations = [migrations.RunPython(backfill_dataset_role_grants, reverse_backfill_dataset_role_grants)]
