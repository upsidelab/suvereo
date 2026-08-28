import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from account.authorization import PERMISSIONS
from account.models import DatasetGroupRoleAssignment, DatasetUserRoleAssignment
from account.tests.helpers import make_group, make_role

pytestmark = pytest.mark.django_db


@pytest.fixture
def subjects(user, data_set):
    """The same scenario expressed for both assignment tables, so each case runs twice."""
    return {
        "user": (DatasetUserRoleAssignment, {"user": user}),
        "group": (DatasetGroupRoleAssignment, {"group": make_group("support")}),
    }


@pytest.mark.parametrize("kind", ["user", "group"])
def test_several_roles_can_be_held_on_one_data_set(subjects, data_set, kind):
    model, subject = subjects[kind]

    model.objects.create(**subject, dataset=data_set, role=make_role("reader", PERMISSIONS.AGENT.VIEW))
    model.objects.create(**subject, dataset=data_set, role=make_role("converser", PERMISSIONS.CONVERSATION.CONVERSE))

    assert model.objects.filter(**subject, dataset=data_set).count() == 2


@pytest.mark.parametrize("kind", ["user", "group"])
def test_the_same_role_cannot_be_held_twice_on_one_data_set(subjects, data_set, kind):
    model, subject = subjects[kind]
    role = make_role("reader", PERMISSIONS.AGENT.VIEW)
    model.objects.create(**subject, dataset=data_set, role=role)

    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.create(**subject, dataset=data_set, role=role)


def test_deleting_a_data_set_takes_its_assignments_with_it(user, data_set):
    role = make_role("reader", PERMISSIONS.AGENT.VIEW)
    DatasetUserRoleAssignment.objects.create(user=user, dataset=data_set, role=role)
    DatasetGroupRoleAssignment.objects.create(group=make_group("support"), dataset=data_set, role=role)

    data_set.delete()

    assert not DatasetUserRoleAssignment.objects.exists()
    assert not DatasetGroupRoleAssignment.objects.exists()


def test_a_role_still_in_use_cannot_be_deleted_through_the_orm(user, data_set):
    role = make_role("reader", PERMISSIONS.AGENT.VIEW)
    DatasetUserRoleAssignment.objects.create(user=user, dataset=data_set, role=role)

    with pytest.raises(ProtectedError), transaction.atomic():
        role.delete()
