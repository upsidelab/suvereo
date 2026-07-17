import tempfile

import pytest
from django.test import override_settings
from model_bakery import baker
from rest_framework.test import APIClient

from account.authorization import set_application_admin
from account.models import User
from agent.models import Conversation
from catalog.models import DataSet


@pytest.fixture
def user():
    return baker.make(User)


@pytest.fixture
def admin_user():
    # is_staff=True stays until every view drops IsAdminUser (removed in the final task)
    user = baker.make(User, is_staff=True)
    set_application_admin(user, True)
    return user


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_api_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def data_set():
    return baker.make(DataSet)


@pytest.fixture
def conversation(user, data_set):
    return baker.make(Conversation, user=user, data_set=data_set)


@pytest.fixture(autouse=True)
def temp_media_root():
    tmp_dir = tempfile.mkdtemp()
    with override_settings(DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage", MEDIA_ROOT=tmp_dir):
        yield
