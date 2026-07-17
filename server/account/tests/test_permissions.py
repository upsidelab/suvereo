import pytest
from model_bakery import baker
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from account.authorization import PERM_MANAGE_USERS, set_application_admin
from account.models import User
from account.permissions import HasRequiredPermission


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
