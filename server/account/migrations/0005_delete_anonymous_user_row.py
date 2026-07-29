from django.db import migrations


def delete_anonymous_user_row(apps, schema_editor):
    """Remove the real User row guardian's post_migrate hook used to create.

    Now that ANONYMOUS_USER_NAME is set to None, guardian no longer creates or
    uses this row, but any dev/staging database that ran migrations before that
    change may still have it lying around, reachable via /api/users.
    """
    User = apps.get_model("account", "User")
    User.objects.filter(email="AnonymousUser", is_service_account=False).delete()


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0004_create_admin_group"),
    ]

    operations = [migrations.RunPython(delete_anonymous_user_row, reverse_noop)]
