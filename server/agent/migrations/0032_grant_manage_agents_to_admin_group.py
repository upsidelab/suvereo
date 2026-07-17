from django.db import migrations

ADMIN_GROUP_NAME = "Admin"
CODENAME = "manage_agents"
NAME = "Can manage agents"


def grant_manage_agents(apps, schema_editor):
    """Create agent.manage_agents explicitly and grant it to the Admin group.

    The permission is created via ContentType because the post_migrate signal
    that materializes Meta.permissions has not run yet within the same migrate
    invocation.
    """
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type, _ = ContentType.objects.get_or_create(app_label="agent", model="agent")
    permission, _ = Permission.objects.get_or_create(
        content_type=content_type, codename=CODENAME, defaults={"name": NAME}
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
    group.permissions.remove(*Permission.objects.filter(codename=CODENAME, content_type__app_label="agent"))


class Migration(migrations.Migration):
    dependencies = [
        ("agent", "0031_alter_agent_options"),
        ("account", "0004_create_admin_group"),
    ]

    operations = [migrations.RunPython(grant_manage_agents, revoke_manage_agents)]
