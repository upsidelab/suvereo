from django.utils.decorators import method_decorator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated

from account.authorization import PERMISSIONS, global_permission_required
from account.models import UserGroup
from account.serializers import GroupDetailSerializer, GroupSerializer

GROUP_ID_PARAMETER = openapi.Parameter("id", openapi.IN_PATH, description="ID of the group", type=openapi.TYPE_INTEGER)


class GroupListView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = UserGroup.objects.with_counts().order_by("name")
    serializer_class = GroupSerializer

    @swagger_auto_schema(operation_description="List all groups")
    @global_permission_required(PERMISSIONS.GROUP.VIEW)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(operation_description="Create a new group", request_body=GroupSerializer)
    @global_permission_required(PERMISSIONS.GROUP.ADD)
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


UPDATE_SCHEMA = swagger_auto_schema(
    operation_description="Update a group's name and description",
    request_body=GroupDetailSerializer,
    manual_parameters=[GROUP_ID_PARAMETER],
)


@method_decorator(name="put", decorator=UPDATE_SCHEMA)
@method_decorator(name="patch", decorator=UPDATE_SCHEMA)
class GroupDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupDetailSerializer
    queryset = UserGroup.objects.with_counts().prefetch_related("global_roles")
    lookup_url_kwarg = "id"

    @swagger_auto_schema(operation_description="Retrieve a group", manual_parameters=[GROUP_ID_PARAMETER])
    @global_permission_required(PERMISSIONS.GROUP.VIEW)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @global_permission_required(PERMISSIONS.GROUP.CHANGE)
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a group, giving up the roles it holds",
        manual_parameters=[GROUP_ID_PARAMETER],
    )
    @global_permission_required(PERMISSIONS.GROUP.DELETE)
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
