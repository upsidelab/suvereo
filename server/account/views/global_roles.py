from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated

from account.authorization import PERMISSIONS, global_permission_required
from account.models import GlobalRole
from account.serializers import GlobalRoleDetailSerializer, GlobalRoleSerializer

GLOBAL_ROLE_ID_PARAMETER = openapi.Parameter("id", openapi.IN_PATH, description="ID of the global role", type=openapi.TYPE_INTEGER)


class GlobalRoleListView(ListCreateAPIView):
    """List global roles; create one with a name, a description and a set of global permissions."""

    permission_classes = [IsAuthenticated]
    queryset = GlobalRole.objects.prefetch_related("permissions__content_type").order_by("name")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return GlobalRoleDetailSerializer
        return GlobalRoleSerializer

    @swagger_auto_schema(operation_description="List all global roles")
    @global_permission_required(PERMISSIONS.GLOBAL_ROLE.VIEW)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(operation_description="Create a new global role", request_body=GlobalRoleDetailSerializer)
    @global_permission_required(PERMISSIONS.GLOBAL_ROLE.ADD)
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class GlobalRoleDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve a global role; update its name, description and permissions; delete it."""

    permission_classes = [IsAuthenticated]
    serializer_class = GlobalRoleDetailSerializer
    queryset = GlobalRole.objects.prefetch_related("permissions__content_type")
    lookup_url_kwarg = "id"

    @swagger_auto_schema(operation_description="Retrieve a global role", manual_parameters=[GLOBAL_ROLE_ID_PARAMETER])
    @global_permission_required(PERMISSIONS.GLOBAL_ROLE.VIEW)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a global role's name, description and permissions",
        request_body=GlobalRoleDetailSerializer,
        manual_parameters=[GLOBAL_ROLE_ID_PARAMETER],
    )
    @global_permission_required(PERMISSIONS.GLOBAL_ROLE.CHANGE)
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a global role, revoking it from everyone holding it",
        manual_parameters=[GLOBAL_ROLE_ID_PARAMETER],
    )
    @global_permission_required(PERMISSIONS.GLOBAL_ROLE.DELETE)
    def delete(self, request, *args, **kwargs):
        """Deleting a global role takes its memberships with it, and takes it off any group
        holding it - what the role held is not a reason the role has to stay."""
        return super().delete(request, *args, **kwargs)
