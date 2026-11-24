from django.utils.decorators import method_decorator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated

from account.authorization import PERMISSIONS, global_permission_required
from account.models import DatasetRole
from account.serializers import DatasetRoleDetailSerializer, DatasetRoleSerializer

DATASET_ROLE_ID_PARAMETER = openapi.Parameter(
    "id", openapi.IN_PATH, description="ID of the dataset role", type=openapi.TYPE_INTEGER
)


class DatasetRoleListView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = DatasetRole.objects.prefetch_related("permissions__content_type").order_by("name")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DatasetRoleDetailSerializer
        return DatasetRoleSerializer

    @swagger_auto_schema(operation_description="List dataset-scoped roles")
    @global_permission_required(PERMISSIONS.DATA_SET_ROLE.VIEW)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new dataset-scoped role", request_body=DatasetRoleDetailSerializer
    )
    @global_permission_required(PERMISSIONS.DATA_SET_ROLE.ADD)
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


UPDATE_SCHEMA = swagger_auto_schema(
    operation_description="Update a dataset role's name, description and permissions",
    request_body=DatasetRoleDetailSerializer,
    manual_parameters=[DATASET_ROLE_ID_PARAMETER],
)


@method_decorator(name="put", decorator=UPDATE_SCHEMA)
@method_decorator(name="patch", decorator=UPDATE_SCHEMA)
class DatasetRoleDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DatasetRoleDetailSerializer
    queryset = DatasetRole.objects.prefetch_related("permissions__content_type")
    lookup_url_kwarg = "id"

    @swagger_auto_schema(
        operation_description="Retrieve a dataset-scoped role", manual_parameters=[DATASET_ROLE_ID_PARAMETER]
    )
    @global_permission_required(PERMISSIONS.DATA_SET_ROLE.VIEW)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @global_permission_required(PERMISSIONS.DATA_SET_ROLE.CHANGE)
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a dataset role, revoking it from everyone who holds it",
        manual_parameters=[DATASET_ROLE_ID_PARAMETER],
    )
    @global_permission_required(PERMISSIONS.DATA_SET_ROLE.DELETE)
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
