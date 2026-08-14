from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from account.authorization import PERMISSIONS, admin_required, any_permission_on_any_dataset_required
from account.models import DatasetGroupRoleAssignment, DatasetRole, DatasetUserRoleAssignment
from account.serializers import DatasetRoleDetailSerializer, DatasetRoleSerializer

DATASET_ROLE_ID_PARAMETER = openapi.Parameter(
    "id", openapi.IN_PATH, description="ID of the dataset role", type=openapi.TYPE_INTEGER
)


class DatasetRoleListView(ListCreateAPIView):
    """List dataset-scoped roles; create one with a name and a set of dataset-scoped permissions."""

    permission_classes = [IsAuthenticated]
    queryset = DatasetRole.objects.prefetch_related("permissions__content_type").order_by("name")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DatasetRoleDetailSerializer
        return DatasetRoleSerializer

    @swagger_auto_schema(operation_description="List dataset-scoped roles")
    @any_permission_on_any_dataset_required(PERMISSIONS.DATASET_ROLE.VIEW, PERMISSIONS.DATASET_ROLE.ASSIGN)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new dataset-scoped role", request_body=DatasetRoleDetailSerializer
    )
    @admin_required
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class DatasetRoleDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve a dataset role; update its name and permissions; delete it."""

    permission_classes = [IsAuthenticated]
    serializer_class = DatasetRoleDetailSerializer
    queryset = DatasetRole.objects.prefetch_related("permissions__content_type")
    lookup_url_kwarg = "id"

    @swagger_auto_schema(
        operation_description="Retrieve a dataset-scoped role", manual_parameters=[DATASET_ROLE_ID_PARAMETER]
    )
    @any_permission_on_any_dataset_required(PERMISSIONS.DATASET_ROLE.VIEW, PERMISSIONS.DATASET_ROLE.ASSIGN)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a dataset role's name and permissions",
        request_body=DatasetRoleDetailSerializer,
        manual_parameters=[DATASET_ROLE_ID_PARAMETER],
    )
    @admin_required
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a dataset role, unless it is still assigned anywhere",
        manual_parameters=[DATASET_ROLE_ID_PARAMETER],
    )
    @admin_required
    def delete(self, request, *args, **kwargs):
        role = self.get_object()
        user_assignments = DatasetUserRoleAssignment.objects.filter(role=role).count()
        group_assignments = DatasetGroupRoleAssignment.objects.filter(role=role).count()
        if user_assignments or group_assignments:
            return Response(
                {
                    "detail": "This role is still assigned. Revoke it everywhere before deleting it.",
                    "user_assignments": user_assignments,
                    "group_assignments": group_assignments,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().delete(request, *args, **kwargs)
