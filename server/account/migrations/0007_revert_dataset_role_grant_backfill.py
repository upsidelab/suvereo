from django.db import migrations


def revert_backfill(apps, schema_editor):
    """Best-effort revert of 0006_backfill_dataset_role_grants.

    Not a perfectly surgical undo: there's no audit trail distinguishing grants 0006
    created from grants added afterward through the normal Roles UI (assign_dataset_role
    always grants a role's full permission set atomically, so re-assigning a role after
    this revert simply re-creates the correct grants). This is a pre-production,
    low-stakes shared dev environment -- the human partner explicitly decided the
    original backfill was unnecessary caution (anyone affected can just re-grant
    themselves via the Roles UI) and asked for it to be reverted, accepting this
    disclosed imprecision rather than leaving 0006's effects in place.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    UserObjectPermission = apps.get_model("guardian", "UserObjectPermission")
    GroupObjectPermission = apps.get_model("guardian", "GroupObjectPermission")

    content_type = ContentType.objects.get(app_label="catalog", model="dataset")
    perms = {
        p.codename: p
        for p in Permission.objects.filter(
            content_type=content_type,
            codename__in=["manage_agents", "converse", "view_integrations", "manage_integrations"],
        )
    }
    manage_agents = perms["manage_agents"]
    converse = perms["converse"]
    view_integrations = perms["view_integrations"]
    manage_integrations = perms["manage_integrations"]

    def revert(model, holder_field):
        editor_tier_pairs = set(model.objects.filter(permission=manage_agents).values_list(holder_field, "object_pk"))
        model.objects.filter(permission=converse).delete()
        for permission in (view_integrations, manage_integrations):
            for holder_id, object_pk in editor_tier_pairs:
                model.objects.filter(**{holder_field: holder_id}, permission=permission, object_pk=object_pk).delete()

    revert(UserObjectPermission, "user_id")
    revert(GroupObjectPermission, "group_id")


def reverse_revert_backfill(apps, schema_editor):
    """No-op: re-running 0006's own forward function is the true undo of this migration,
    and that logic already lives in 0006 -- not duplicated here."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0006_backfill_dataset_role_grants"),
    ]

    operations = [migrations.RunPython(revert_backfill, reverse_revert_backfill)]
