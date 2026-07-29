import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_migrate_users_to_editor_grants_creates_permission_and_backfills_grants():
    """Regression test: catalog.0015 must correctly backfill DataSet.users rows into
    guardian editor grants (access_dataset + manage_agents) even when neither
    Permission row exists yet, since Meta.permissions are only materialized by
    post_migrate once the whole migrate invocation ends -- a single-shot `migrate`
    reaching this migration's RunPython step has no such rows yet.
    """
    executor = MigrationExecutor(connection)

    # Migrate back to just before catalog's squashed permissions/access-grants
    # migration, so DataSet.users (the M2M) still exists -- reproducing the state
    # the original bug occurred in.
    executor.migrate([("catalog", "0014_drop_domain_tables_add_integration")])
    executor.loader.build_graph()

    # Pin account explicitly to its own latest pre-0015 state too: nothing in
    # catalog's migration graph up to 0014 depends on account, so leaving it
    # unpinned resolves to account's earliest state (no is_service_account field
    # yet), not "whatever account looks like right before catalog 0015 runs".
    old_apps = executor.loader.project_state(
        [("catalog", "0014_drop_domain_tables_add_integration"), ("account", "0002_user_is_service_account")]
    ).apps
    OldDataSet = old_apps.get_model("catalog", "DataSet")
    OldUser = old_apps.get_model("account", "User")

    # pytest-django creates the test database by running the *full* migration
    # history up front (post_migrate included), so catalog.access_dataset already
    # exists as a Permission row by the time this test starts. That's not the state
    # the original bug occurred in -- a single-shot `migrate` reaching this migration
    # has no such row yet, since post_migrate only fires once the whole invocation
    # ends. Delete it so the forward migration below starts from the genuinely
    # broken state.
    from django.contrib.auth.models import Permission

    Permission.objects.filter(content_type__app_label="catalog", codename="access_dataset").delete()

    user = OldUser.objects.create(email="migrationtest@example.com")
    dataset = OldDataSet.objects.create(name="Pre-migration dataset")
    dataset.users.add(user)

    # Forward through the squashed migration -- this must not raise (the original
    # bug: Permission.DoesNotExist).
    executor = MigrationExecutor(connection)
    executor.migrate([("catalog", "0015_dataset_permissions_and_access_grants")])

    from django.contrib.auth.models import Permission
    from guardian.shortcuts import get_perms

    from account.models import User as LiveUser
    from catalog.models import DataSet as LiveDataSet

    assert Permission.objects.filter(content_type__app_label="catalog", codename="access_dataset").exists()

    live_user = LiveUser.objects.get(email="migrationtest@example.com")
    live_dataset = LiveDataSet.objects.get(name="Pre-migration dataset")
    perms = set(get_perms(live_user, live_dataset))
    assert perms == {"access_dataset", "manage_agents"}

    # Restore to the latest migration state so later tests in the same run aren't
    # left on a partially-migrated schema.
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    targets = executor.loader.graph.leaf_nodes()
    executor.migrate(targets)
