import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from account.authorization import PERM_MANAGE_USERS, set_application_admin
from account.models import User
from account.permissions import HasRequiredPermission, IsApplicationAdmin


class _ProtectedView(APIView):
    permission_classes = [HasRequiredPermission]
    required_permission = PERM_MANAGE_USERS

    def get(self, request):
        return Response({"ok": True})


class _MisconfiguredView(APIView):
    permission_classes = [HasRequiredPermission]

    def get(self, request):
        return Response({"ok": True})


def _get(view_class, user):
    request = APIRequestFactory().get("/")
    force_authenticate(request, user=user)
    return view_class.as_view()(request)


@pytest.mark.django_db
class TestHasRequiredPermission:
    def test_allows_user_with_permission(self):
        user = baker.make(User)
        set_application_admin(user, True)
        user = User.objects.get(pk=user.pk)  # fresh instance: has_perm caches per object
        assert _get(_ProtectedView, user).status_code == 200

    def test_denies_user_without_permission(self):
        user = baker.make(User)
        assert _get(_ProtectedView, user).status_code == 403

    def test_denies_staff_only_user(self):
        user = baker.make(User, is_staff=True)
        assert _get(_ProtectedView, user).status_code == 403

    def test_denies_when_view_lacks_required_permission_attribute(self):
        user = baker.make(User)
        set_application_admin(user, True)
        user = User.objects.get(pk=user.pk)
        assert _get(_MisconfiguredView, user).status_code == 403


class _AdminOnlyView(APIView):
    permission_classes = [IsApplicationAdmin]

    def get(self, request):
        return Response({"ok": True})


@pytest.mark.django_db
class TestIsApplicationAdmin:
    def test_allows_admin_group_member(self, admin_user):
        request = APIRequestFactory().get("/")
        force_authenticate(request, user=admin_user)
        assert _AdminOnlyView.as_view()(request).status_code == 200

    def test_denies_regular_user(self):
        user = baker.make(User)
        request = APIRequestFactory().get("/")
        force_authenticate(request, user=user)
        assert _AdminOnlyView.as_view()(request).status_code == 403

    def test_denies_manage_datasets_holder_who_is_not_in_admin_group(self):
        from django.contrib.auth.models import Permission

        user = baker.make(User)
        user.user_permissions.add(Permission.objects.get(content_type__app_label="catalog", codename="manage_datasets"))
        user = User.objects.get(pk=user.pk)
        request = APIRequestFactory().get("/")
        force_authenticate(request, user=user)
        assert _AdminOnlyView.as_view()(request).status_code == 403


@pytest.mark.django_db
class TestPermissionListView:
    def test_global_scope_returns_the_six_admin_permissions(self, admin_api_client):
        response = admin_api_client.get(reverse("permission_list"), {"scope": "global"})
        assert response.status_code == status.HTTP_200_OK
        codenames = {row["codename"] for row in response.data}
        assert codenames == {
            "account.manage_users",
            "account.manage_service_accounts",
            "catalog.manage_datasets",
            "catalog.access_all_datasets",
            "catalog.configure_models",
            "catalog.manage_agents",
        }

    def test_dataset_scope_returns_only_dataset_permissions(self, admin_api_client):
        response = admin_api_client.get(reverse("permission_list"), {"scope": "dataset"})
        codenames = {row["codename"] for row in response.data}
        assert codenames == {"catalog.access_dataset", "catalog.manage_agents"}

    def test_missing_scope_returns_empty_list(self, admin_api_client):
        response = admin_api_client.get(reverse("permission_list"))
        assert response.data == []

    def test_regular_user_forbidden(self, api_client):
        response = api_client.get(reverse("permission_list"), {"scope": "global"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
