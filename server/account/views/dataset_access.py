from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.authorization import PERMISSIONS, global_permission_required
from account.models import DatasetGlobalRoleAssignment, DatasetRole, DatasetUserRoleAssignment
from account.serializers import (
    DatasetGlobalRoleAssignmentSerializer,
    DatasetUserRoleAssignmentSerializer,
    GlobalRoleReferenceSerializer,
    UserReferenceSerializer,
)
from catalog.models import DataSet

DATA_SET_ID_PARAMETER = openapi.Parameter(
    "data_set_id", openapi.IN_PATH, description="ID of the data set", type=openapi.TYPE_INTEGER
)
ROLE_ID_PARAMETER = openapi.Parameter(
    "role_id", openapi.IN_PATH, description="ID of the dataset role", type=openapi.TYPE_INTEGER
)


class _DatasetAccessView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_dataset(self, data_set_id):
        return get_object_or_404(DataSet, pk=data_set_id)

    def _get_dataset_and_role(self, data_set_id, role_id):
        data_set = self._get_dataset(data_set_id)
        return data_set, get_object_or_404(DatasetRole, pk=role_id)


class DatasetAccessListView(_DatasetAccessView):
    @swagger_auto_schema(
        operation_description="List the role assignments on a data set",
        manual_parameters=[DATA_SET_ID_PARAMETER],
    )
    @global_permission_required(PERMISSIONS.DATASET_ROLE.ASSIGN)
    def get(self, request, data_set_id):
        data_set = self._get_dataset(data_set_id)
        users = DatasetUserRoleAssignment.objects.filter(dataset=data_set).select_related("user", "role")
        global_roles = DatasetGlobalRoleAssignment.objects.filter(dataset=data_set).select_related(
            "global_role", "role"
        )
        return Response(
            {
                "users": DatasetUserRoleAssignmentSerializer(users, many=True).data,
                "global_roles": DatasetGlobalRoleAssignmentSerializer(global_roles, many=True).data,
            }
        )


class DatasetRoleUserListView(_DatasetAccessView):
    @swagger_auto_schema(
        operation_description="Grant this role on this data set to a user",
        request_body=UserReferenceSerializer,
        manual_parameters=[DATA_SET_ID_PARAMETER, ROLE_ID_PARAMETER],
    )
    @global_permission_required(PERMISSIONS.DATASET_ROLE.ASSIGN)
    def post(self, request, data_set_id, role_id):
        data_set, role = self._get_dataset_and_role(data_set_id, role_id)
        serializer = UserReferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assignment, created = DatasetUserRoleAssignment.objects.get_or_create(
            user=serializer.validated_data["user"], dataset=data_set, role=role
        )
        return Response(
            DatasetUserRoleAssignmentSerializer(assignment).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class DatasetRoleUserView(_DatasetAccessView):
    @swagger_auto_schema(
        operation_description="Revoke this role on this data set from a user",
        manual_parameters=[
            DATA_SET_ID_PARAMETER,
            ROLE_ID_PARAMETER,
            openapi.Parameter("user_id", openapi.IN_PATH, description="ID of the user", type=openapi.TYPE_INTEGER),
        ],
    )
    @global_permission_required(PERMISSIONS.DATASET_ROLE.ASSIGN)
    def delete(self, request, data_set_id, role_id, user_id):
        data_set = self._get_dataset(data_set_id)
        assignment = get_object_or_404(
            DatasetUserRoleAssignment, user_id=user_id, dataset=data_set, role_id=role_id
        )
        assignment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DatasetRoleGlobalRoleListView(_DatasetAccessView):
    @swagger_auto_schema(
        operation_description="Grant this role on this data set to a global role",
        request_body=GlobalRoleReferenceSerializer,
        manual_parameters=[DATA_SET_ID_PARAMETER, ROLE_ID_PARAMETER],
    )
    @global_permission_required(PERMISSIONS.DATASET_ROLE.ASSIGN)
    def post(self, request, data_set_id, role_id):
        data_set, role = self._get_dataset_and_role(data_set_id, role_id)
        serializer = GlobalRoleReferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assignment, created = DatasetGlobalRoleAssignment.objects.get_or_create(
            global_role=serializer.validated_data["global_role"], dataset=data_set, role=role
        )
        return Response(
            DatasetGlobalRoleAssignmentSerializer(assignment).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class DatasetRoleGlobalRoleView(_DatasetAccessView):
    @swagger_auto_schema(
        operation_description="Revoke this role on this data set from a global role",
        manual_parameters=[
            DATA_SET_ID_PARAMETER,
            ROLE_ID_PARAMETER,
            openapi.Parameter("global_role_id", openapi.IN_PATH, description="ID of the global role", type=openapi.TYPE_INTEGER),
        ],
    )
    @global_permission_required(PERMISSIONS.DATASET_ROLE.ASSIGN)
    def delete(self, request, data_set_id, role_id, global_role_id):
        data_set = self._get_dataset(data_set_id)
        assignment = get_object_or_404(
            DatasetGlobalRoleAssignment, global_role_id=global_role_id, dataset=data_set, role_id=role_id
        )
        assignment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
