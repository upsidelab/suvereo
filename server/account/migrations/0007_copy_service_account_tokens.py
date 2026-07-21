from django.db import migrations


def copy_service_account_tokens(apps, schema_editor):
    """Copy remaining rest_framework.authtoken.Token rows into AuthToken.

    Migration 0005 already deleted every human-user token, so only
    service-account tokens remain in the old table at this point. Keys are
    preserved so existing external integrations keep working unchanged.
    """
    OldToken = apps.get_model("authtoken", "Token")
    AuthToken = apps.get_model("account", "AuthToken")

    for old_token in OldToken.objects.all():
        AuthToken.objects.create(user=old_token.user, key=old_token.key, expires_at=None)


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0006_authtoken"),
        ("authtoken", "0004_alter_tokenproxy_options"),
    ]

    operations = [migrations.RunPython(copy_service_account_tokens, migrations.RunPython.noop)]
