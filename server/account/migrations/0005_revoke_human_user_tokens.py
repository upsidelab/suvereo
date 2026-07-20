from django.db import migrations


def revoke_human_user_tokens(apps, schema_editor):
    """Delete API tokens belonging to non-service-account users.

    Human users now authenticate via session cookie instead of a token used
    directly by the frontend; any leftover Token row for a human user must be
    revoked so a token stolen before this migration (e.g. via XSS) stops
    working once this deploy lands.
    """
    Token = apps.get_model("authtoken", "Token")
    Token.objects.filter(user__is_service_account=False).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0004_create_admin_group"),
        ("authtoken", "0004_alter_tokenproxy_options"),
    ]

    operations = [migrations.RunPython(revoke_human_user_tokens, migrations.RunPython.noop)]
