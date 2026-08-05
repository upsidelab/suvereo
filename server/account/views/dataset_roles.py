from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response

from account.authorization import count_datasets_using_role, revoke_dataset_role_everywhere
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
    """Retrieve/update a dataset role's name and permissions; delete it (revokes it from every
    grant currently using it. See DatasetRoleUsageView for the count shown before deleting)."""

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

    @swagger_auto_schema(
        operation_description="Delete a dataset role, revoking it from every (user/group, dataset) grant "
        "currently using it"
    )
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        revoke_dataset_role_everywhere(instance.name)
        return super().delete(request, *args, **kwargs)


class DatasetRoleUsageView(GenericAPIView):
    """Read-only: how many (user/group, dataset) grants currently use this role. Lets the
    frontend warn before a delete revokes access, the same way GroupMembersView does for Groups.
    """

    permission_classes = [IsApplicationAdmin]

    @swagger_auto_schema(operation_description="Count grants currently using this dataset role")
    def get(self, request, dataset_role_id):
        role = get_object_or_404(DatasetRole, pk=dataset_role_id)
        return Response({"count": count_datasets_using_role(role.name)})
