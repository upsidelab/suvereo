from django.contrib.auth.models import Group
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from account.authorization import PERMISSIONS, admin_required, global_permission_required
from account.models import DatasetGroupRoleAssignment
from account.serializers import GroupDetailSerializer, GroupSerializer

GROUP_ID_PARAMETER = openapi.Parameter("id", openapi.IN_PATH, description="ID of the group", type=openapi.TYPE_INTEGER)


class GroupListView(ListCreateAPIView):
    """List groups; create one with a name and a set of global permissions."""

    permission_classes = [IsAuthenticated]
    queryset = Group.objects.prefetch_related("permissions__content_type").order_by("name")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return GroupDetailSerializer
        return GroupSerializer

    @swagger_auto_schema(operation_description="List all groups")
    @global_permission_required(PERMISSIONS.GROUP.VIEW)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(operation_description="Create a new group", request_body=GroupDetailSerializer)
    @admin_required
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class GroupDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve a group; update its name and permissions; delete it."""

    permission_classes = [IsAuthenticated]
    serializer_class = GroupDetailSerializer
    queryset = Group.objects.prefetch_related("permissions__content_type")
    lookup_url_kwarg = "id"

    @swagger_auto_schema(operation_description="Retrieve a group", manual_parameters=[GROUP_ID_PARAMETER])
    @global_permission_required(PERMISSIONS.GROUP.VIEW)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a group's name and permissions",
        request_body=GroupDetailSerializer,
        manual_parameters=[GROUP_ID_PARAMETER],
    )
    @admin_required
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a group, unless it still holds a role on a data set",
        manual_parameters=[GROUP_ID_PARAMETER],
    )
    @admin_required
    def delete(self, request, *args, **kwargs):
        group = self.get_object()
        assignment_count = DatasetGroupRoleAssignment.objects.filter(group=group).count()
        if assignment_count:
            return Response(
                {
                    "detail": "This group still holds a role on one or more data sets. Revoke those first.",
                    "dataset_assignments": assignment_count,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().delete(request, *args, **kwargs)
