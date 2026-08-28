import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from account.authorization import PERMISSIONS
from account.models import DatasetRole, User
from account.tests.helpers import client_for, grant

pytestmark = pytest.mark.django_db

TAKEN_NAME = "already-taken"


@pytest.fixture
def existing_group():
    return Group.objects.create(name=TAKEN_NAME)


@pytest.fixture
def existing_role():
    return DatasetRole.objects.create(name=TAKEN_NAME)


@pytest.fixture
def target_user():
    return baker.make(User, email="taken@example.com", is_service_account=False)


@pytest.fixture
def guarded_writes(existing_group, existing_role, target_user):
    """Every guarded write, paired with a body that an authorised caller would be told is invalid."""
    return {
        "POST /api/groups (name taken)": ("post", reverse("group_list"), {"name": TAKEN_NAME}),
        "POST /api/groups (name free)": ("post", reverse("group_list"), {"name": "brand-new"}),
        "PATCH /api/groups/<id> (name taken)": (
            "patch",
            reverse("group_details", args=[existing_group.id]),
            {"name": TAKEN_NAME},
        ),
        "PUT /api/groups/<id> (name taken)": (
            "put",
            reverse("group_details", args=[existing_group.id]),
            {"name": TAKEN_NAME},
        ),
        "POST /api/dataset_roles (name taken)": ("post", reverse("dataset_role_list"), {"name": TAKEN_NAME}),
        "POST /api/users (invalid email)": (
            "post",
            reverse("user_list"),
            {"email": "not-an-email", "password": "x", "is_active": True, "is_admin": False},
        ),
        "PATCH /api/users/<id> (invalid email)": (
            "patch",
            reverse("user_details", args=[target_user.id]),
            {"email": "not-an-email"},
        ),
        "POST /api/data_sets (missing name)": ("post", reverse("data_set_list"), {}),
    }


class TestAnUnauthorisedCallerIsRefusedBeforeValidation:
    @pytest.mark.parametrize(
        "endpoint",
        [
            "POST /api/groups (name taken)",
            "POST /api/groups (name free)",
            "PATCH /api/groups/<id> (name taken)",
            "PUT /api/groups/<id> (name taken)",
            "POST /api/dataset_roles (name taken)",
            "POST /api/users (invalid email)",
            "PATCH /api/users/<id> (invalid email)",
            "POST /api/data_sets (missing name)",
        ],
    )
    def test_an_invalid_body_still_gets_403(self, user, guarded_writes, endpoint):
        method, url, body = guarded_writes[endpoint]

        response = getattr(client_for(user), method)(url, body, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_a_taken_name_is_indistinguishable_from_a_free_one(self, user, guarded_writes):
        client = client_for(user)
        _, url, taken = guarded_writes["POST /api/groups (name taken)"]
        _, _, free = guarded_writes["POST /api/groups (name free)"]

        taken_response = client.post(url, taken, format="json")
        free_response = client.post(url, free, format="json")

        assert taken_response.status_code == free_response.status_code
        assert taken_response.data == free_response.data


class TestAnAuthorisedCallerStillSeesValidationErrors:
    """The other half: the guard moved earlier, it did not swallow the validation."""

    def test_an_admin_creating_a_group_with_a_taken_name_gets_400(self, admin_api_client, existing_group):
        response = admin_api_client.post(reverse("group_list"), {"name": TAKEN_NAME}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert str(response.data["name"][0]) == "group with this name already exists."

    def test_an_admin_creating_a_dataset_role_with_a_taken_name_gets_400(self, admin_api_client, existing_role):
        response = admin_api_client.post(reverse("dataset_role_list"), {"name": TAKEN_NAME}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "name" in response.data

    def test_a_user_add_holder_posting_a_malformed_email_gets_400(self, user):
        grant(user, PERMISSIONS.USER.VIEW, PERMISSIONS.USER.ADD)

        response = client_for(user).post(
            reverse("user_list"),
            {"email": "not-an-email", "password": "s3cret-pass", "is_active": True, "is_admin": False},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data
