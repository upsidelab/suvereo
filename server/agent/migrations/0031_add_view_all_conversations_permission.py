from django.db import migrations

ADMIN_GROUP_NAME = "Admin"
CODENAME = "view_all_conversations"
NAME = "Can view every user's conversations"


def add_view_all_conversations_permission(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")

    content_type, _ = ContentType.objects.get_or_create(app_label="agent", model="conversation")
    permission, _ = Permission.objects.get_or_create(
        content_type=content_type, codename=CODENAME, defaults={"name": NAME}
    )
    group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
    group.permissions.add(permission)


def remove_view_all_conversations_permission(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    try:
        group = Group.objects.get(name=ADMIN_GROUP_NAME)
    except Group.DoesNotExist:
        return
    group.permissions.remove(*Permission.objects.filter(codename=CODENAME, content_type__app_label="agent"))


class Migration(migrations.Migration):
    dependencies = [
        ("agent", "0030_conversation_ai_summary"),
        ("account", "0003_admin_group_and_dataset_role"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="conversation",
            options={
                "db_table_comment": (
                    "A conversation is a collection of various messages exchanged during one session. Messages "
                    "are mostly questions and answers and have different actors such as end user asking "
                    "question and ECL agent answering those questions."
                ),
                "permissions": [("view_all_conversations", "Can view every user's conversations")],
            },
        ),
        migrations.RunPython(add_view_all_conversations_permission, remove_view_all_conversations_permission),
    ]
