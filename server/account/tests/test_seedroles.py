from io import StringIO

import pytest
from django.core.management import call_command

from account.authorization import DATASET_SCOPE_PERMISSIONS, GLOBAL_SCOPE_PERMISSIONS, missing_dependencies
from account.models import DatasetRole, GlobalRole
from account.seeds import STARTER_DATA_SET_ROLES, STARTER_GLOBAL_ROLES

pytestmark = pytest.mark.django_db

STARTER_SETS = [
    (STARTER_GLOBAL_ROLES, GLOBAL_SCOPE_PERMISSIONS),
    (STARTER_DATA_SET_ROLES, DATASET_SCOPE_PERMISSIONS),
]


def seed(*arguments) -> str:
    output = StringIO()
    call_command("seedroles", *arguments, stdout=output)
    return output.getvalue()


@pytest.mark.parametrize(("starter_roles", "scope"), STARTER_SETS)
def test_every_starter_role_is_one_the_role_editor_would_accept(starter_roles, scope):
    for starter in starter_roles:
        assert set(starter.permissions) <= set(scope), starter.name
        assert not missing_dependencies(set(starter.permissions), scope), starter.name


def test_it_creates_the_starter_roles_with_their_permissions_and_descriptions():
    seed()

    assert DatasetRole.objects.count() == len(STARTER_DATA_SET_ROLES)
    for starter in STARTER_GLOBAL_ROLES:
        role = GlobalRole.objects.get(name=starter.name)
        assert {permission.codename for permission in role.permissions.all()} == {
            code.split(".")[1] for code in starter.permissions
        }
        assert role.description == starter.description


def test_re_running_reports_an_edited_role_and_leaves_it_alone():
    seed()
    GlobalRole.objects.filter(name="Management").update(description="Ours now.")

    output = seed()

    assert "Management: skipped, differs from starter set (description)" in output
    assert GlobalRole.objects.get(name="Management").description == "Ours now."
    assert GlobalRole.objects.count() == len(STARTER_GLOBAL_ROLES)


def test_a_deleted_role_comes_back():
    seed()
    GlobalRole.objects.filter(name="Access Management").delete()

    assert "Access Management: created" in seed()


def test_a_dry_run_writes_nothing():
    output = seed("--dry-run")

    assert not GlobalRole.objects.exists()
    assert not DatasetRole.objects.exists()
    assert "Agent Interaction: created" in output
