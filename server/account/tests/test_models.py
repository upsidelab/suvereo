import pytest
from django.db import IntegrityError, transaction

from account.authorization import PERMISSIONS
from account.models import DatasetGlobalRoleAssignment, DatasetUserRoleAssignment
from account.tests.helpers import make_global_role, make_role

pytestmark = pytest.mark.django_db


@pytest.fixture
def subjects(user, data_set):
    """The same scenario expressed for both assignment tables, so each case runs twice."""
    return {
        "user": (DatasetUserRoleAssignment, {"user": user}),
        "global_role": (DatasetGlobalRoleAssignment, {"global_role": make_global_role("support")}),
    }


@pytest.mark.parametrize("kind", ["user", "global_role"])
def test_several_roles_can_be_held_on_one_data_set(subjects, data_set, kind):
    model, subject = subjects[kind]

    model.objects.create(**subject, dataset=data_set, role=make_role("reader", PERMISSIONS.AGENT.VIEW))
    model.objects.create(**subject, dataset=data_set, role=make_role("converser", PERMISSIONS.CONVERSATION.CONVERSE))

    assert model.objects.filter(**subject, dataset=data_set).count() == 2


@pytest.mark.parametrize("kind", ["user", "global_role"])
def test_the_same_role_cannot_be_held_twice_on_one_data_set(subjects, data_set, kind):
    model, subject = subjects[kind]
    role = make_role("reader", PERMISSIONS.AGENT.VIEW)
    model.objects.create(**subject, dataset=data_set, role=role)

    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.create(**subject, dataset=data_set, role=role)


def test_deleting_a_data_set_takes_its_assignments_with_it(user, data_set):
    role = make_role("reader", PERMISSIONS.AGENT.VIEW)
    DatasetUserRoleAssignment.objects.create(user=user, dataset=data_set, role=role)
    DatasetGlobalRoleAssignment.objects.create(global_role=make_global_role("support"), dataset=data_set, role=role)

    data_set.delete()

    assert not DatasetUserRoleAssignment.objects.exists()
    assert not DatasetGlobalRoleAssignment.objects.exists()


def test_deleting_a_role_takes_its_assignments_with_it(user, data_set):
    role = make_role("reader", PERMISSIONS.AGENT.VIEW)
    DatasetUserRoleAssignment.objects.create(user=user, dataset=data_set, role=role)
    DatasetGlobalRoleAssignment.objects.create(global_role=make_global_role("support"), dataset=data_set, role=role)

    role.delete()

    assert not DatasetUserRoleAssignment.objects.exists()
    assert not DatasetGlobalRoleAssignment.objects.exists()
