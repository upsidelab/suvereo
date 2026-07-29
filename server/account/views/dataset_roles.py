from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response

from account.authorization import count_datasets_using_role
from account.models import DatasetRole
from account.permissions import IsApplicationAdmin
from account.serializers import DatasetRoleDetailSerializer, DatasetRoleSerializer


class DatasetRoleListView(ListCreateAPIView):
    """List every dataset-scoped role; create a new one (name + permission_ids)."""

    permission_classes = [IsApplicationAdmin]
    queryset = DatasetRole.objects.all().order_by("name")
    pagination_class = None

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DatasetRoleDetailSerializer
        return DatasetRoleSerializer

    @swagger_auto_schema(operation_description="List dataset-scoped roles")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new dataset-scoped role", request_body=DatasetRoleDetailSerializer
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class DatasetRoleDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve/update a dataset role's name and permissions; delete it (blocked while
    seeded/system or in use)."""

    permission_classes = [IsApplicationAdmin]
    serializer_class = DatasetRoleDetailSerializer
    queryset = DatasetRole.objects.all()
    lookup_url_kwarg = "dataset_role_id"

    @swagger_auto_schema(operation_description="Retrieve a dataset-scoped role")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a dataset role's name/permissions", request_body=DatasetRoleDetailSerializer
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(operation_description="Delete a dataset role (blocked while seeded/system or in use)")
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_system:
            return Response({"detail": "System dataset roles cannot be deleted."}, status=status.HTTP_400_BAD_REQUEST)
        usage_count = count_datasets_using_role(instance.name)
        if usage_count > 0:
            return Response(
                {"detail": f"{usage_count} dataset(s) currently use this role; remove those grants first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().delete(request, *args, **kwargs)
