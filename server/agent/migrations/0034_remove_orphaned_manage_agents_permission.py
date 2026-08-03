from django.db import migrations


def remove_orphaned_manage_agents_permission(apps, schema_editor):
    """Delete the orphaned `agent.agent` "manage_agents" Permission row.

    Created by 0031_alter_agent_options.py's now-reverted Meta.permissions entry,
    cleared the same day by 0032_alter_agent_options.py once guardian's per-object
    content-type-matching constraint moved this concept onto catalog.DataSet instead.
    AlterModelOptions only updates migration state -- it never deletes an
    already-created Permission row -- so this stray row (and an Admin group grant
    of it, made while it briefly existed) survived undetected. Its bare codename
    "manage_agents" collided with catalog.DataSet's real manage_agents permission
    in PermissionListView's composer query (see account/views/permissions.py's
    content-type-aware fix in the same commit as this migration), showing a
    duplicate, description-less "Can manage agents" checkbox in the Roles UI
    alongside the real "Can manage agents in this data set" entry.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")

    try:
        content_type = ContentType.objects.get(app_label="agent", model="agent")
        permission = Permission.objects.get(content_type=content_type, codename="manage_agents")
    except (ContentType.DoesNotExist, Permission.DoesNotExist):
        return

    for group in permission.group_set.all():
        group.permissions.remove(permission)
    for user in permission.user_set.all():
        user.user_permissions.remove(permission)
    permission.delete()


def reverse_noop(apps, schema_editor):
    """No-op: recreating a permission that was never supposed to exist isn't a
    meaningful reverse. If agent.Agent's Meta.permissions is ever restored to
    declare "manage_agents" again, Django's own migration/post_migrate machinery
    recreates the row on its own."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("agent", "0033_add_view_all_conversations_permission"),
    ]

    operations = [migrations.RunPython(remove_orphaned_manage_agents_permission, reverse_noop)]
