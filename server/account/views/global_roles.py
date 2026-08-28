from django.contrib.auth.models import Group
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated

from account.authorization import PERMISSIONS, admin_required, global_permission_required
from account.serializers import GlobalRoleDetailSerializer, GlobalRoleSerializer

GLOBAL_ROLE_ID_PARAMETER = openapi.Parameter("id", openapi.IN_PATH, description="ID of the global role", type=openapi.TYPE_INTEGER)


class GlobalRoleListView(ListCreateAPIView):
    """List groups; create one with a name and a set of global permissions."""

    permission_classes = [IsAuthenticated]
    queryset = Group.objects.prefetch_related("permissions__content_type").order_by("name")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return GlobalRoleDetailSerializer
        return GlobalRoleSerializer

    @swagger_auto_schema(operation_description="List all groups")
    @global_permission_required(PERMISSIONS.GLOBAL_ROLE.VIEW)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(operation_description="Create a new group", request_body=GlobalRoleDetailSerializer)
    @admin_required
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class GlobalRoleDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve a group; update its name and permissions; delete it."""

    permission_classes = [IsAuthenticated]
    serializer_class = GlobalRoleDetailSerializer
    queryset = Group.objects.prefetch_related("permissions__content_type")
    lookup_url_kwarg = "id"

    @swagger_auto_schema(operation_description="Retrieve a group", manual_parameters=[GLOBAL_ROLE_ID_PARAMETER])
    @global_permission_required(PERMISSIONS.GLOBAL_ROLE.VIEW)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a group's name and permissions",
        request_body=GlobalRoleDetailSerializer,
        manual_parameters=[GLOBAL_ROLE_ID_PARAMETER],
    )
    @admin_required
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a group, giving up the roles it holds on data sets",
        manual_parameters=[GLOBAL_ROLE_ID_PARAMETER],
    )
    @admin_required
    def delete(self, request, *args, **kwargs):
        """Deleting a group takes its memberships and its dataset role assignments with it - what
        the group held is not a reason the group has to stay."""
        return super().delete(request, *args, **kwargs)
