import pytest
from guardian.shortcuts import assign_perm
from model_bakery import baker

from account.models import User
from catalog.models import DataSet


@pytest.mark.django_db
class TestGuardianObjectPermissions:
    def test_object_scoped_grant_applies_only_to_the_granted_dataset(self):
        user = baker.make(User)
        dataset_a = baker.make(DataSet)
        dataset_b = baker.make(DataSet)

        assign_perm("catalog.access_dataset", user, dataset_a)

        assert user.has_perm("catalog.access_dataset", dataset_a) is True
        assert user.has_perm("catalog.access_dataset", dataset_b) is False

    def test_object_scoped_grant_does_not_leak_into_the_global_check(self):
        user = baker.make(User)
        dataset = baker.make(DataSet)

        assign_perm("catalog.access_dataset", user, dataset)

        assert user.has_perm("catalog.access_dataset") is False
