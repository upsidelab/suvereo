from django.apps import apps as installed_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

PERMISSION_NAMES = {
    "catalog.view_dataset": "See every data set and its configuration",
    "catalog.add_dataset": "Create data sets",
    "catalog.change_dataset": "Edit a data set's name and language model",
    "catalog.delete_dataset": "Delete data sets, with everything they contain",
    "agent.view_agent": "See the agents configured on a data set",
    "agent.add_agent": "Add agents to a data set",
    "agent.change_agent": "Edit an agent's configuration",
    "agent.delete_agent": "Delete agents from a data set",
    "catalog.view_integration": "See the integrations configured on a data set",
    "catalog.add_integration": "Add integrations to a data set",
    "catalog.change_integration": "Edit an integration's configuration",
    "catalog.delete_integration": "Delete integrations from a data set",
    "catalog.sync_integration": "Start a synchronization for an integration",
    "agent.converse": "Start conversations with agents, and read your own history",
    "agent.view_conversation": "Read everyone's conversations on a data set",
    "agent.add_agenticexecution": "Run agentic executions, and see the ones you started",
    "agent.view_agenticexecution": "See everyone's agentic executions on a data set",
    "account.view_user": "See the list of user accounts",
    "account.add_user": "Create user accounts",
    "account.change_user": "Edit user accounts and reset their passwords",
    "account.view_serviceaccount": "See the list of service accounts",
    "account.add_serviceaccount": "Create service accounts",
    "account.change_serviceaccount": "Edit service accounts and reset their tokens",
    "account.view_datasetrole": "See the data set roles that can be granted",
    "account.assign_datasetrole": "Grant and revoke data set roles on a data set",
}


def set_permission_names(apps, schema_editor):
    """Renames every permission in the public vocabulary.

    On a fresh database the rows do not exist yet - Django creates them from `post_migrate`, which
    runs after every migration - so each involved app's permissions are created here first and then
    renamed. On an existing database the creation pass finds nothing to do and only the rename runs.
    """
    for app_label in sorted({code.split(".")[0] for code in PERMISSION_NAMES}):
        create_permissions(installed_apps.get_app_config(app_label), verbosity=0)

    permission_model = apps.get_model("auth", "Permission")
    for code, name in PERMISSION_NAMES.items():
        app_label, codename = code.split(".")
        permission_model.objects.filter(content_type__app_label=app_label, codename=codename).update(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0006_composable_dataset_roles"),
        ("agent", "0031_conversation_converse_permission"),
        ("catalog", "0016_integration_sync_permission"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(set_permission_names, migrations.RunPython.noop)]
