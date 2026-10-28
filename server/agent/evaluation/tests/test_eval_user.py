from unittest.mock import patch

import pytest
from django.db.models import QuerySet

from account.models import User
from agent.evaluation.eval_user import EvalUser

pytestmark = pytest.mark.django_db


class TestEvalUser:
    def test_is_one_account_that_cannot_log_in(self):
        user = EvalUser.get()

        assert EvalUser.get() == user
        assert user.is_service_account
        assert not user.is_active
        assert not user.has_usable_password()
        assert user.is_internal

    def test_is_hidden_from_normal_lookups(self):
        user = EvalUser.get()

        assert not User.objects.filter(pk=user.pk).exists()
        assert User.all_objects.filter(pk=user.pk).exists()

    def test_an_account_created_concurrently_is_reused(self):
        existing = User.objects.create_service_account(EvalUser.email(), is_active=False, is_internal=True)

        with patch.object(QuerySet, "first", return_value=None):
            assert EvalUser.get() == existing
