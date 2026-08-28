from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.authorization import PERMISSIONS, global_permission_required
from account.models import DatasetGroupRoleAssignment, DatasetRole, DatasetUserRoleAssignment, UserGroup
from account.serializers import (
    DatasetGroupRoleAssignmentSerializer,
    DatasetUserRoleAssignmentSerializer,
    GroupReferenceSerializer,
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
    @global_permission_required(PERMISSIONS.DATA_SET_ROLE.ASSIGN)
    def get(self, request, data_set_id):
        data_set = self._get_dataset(data_set_id)
        members = DatasetUserRoleAssignment.objects.filter(dataset=data_set).select_related("user", "role")
        groups = (
            DatasetGroupRoleAssignment.objects.filter(dataset=data_set)
            .select_related("role")
            .prefetch_related(Prefetch("group", queryset=UserGroup.objects.with_counts()))
        )
        return Response(
            {
                "members": DatasetUserRoleAssignmentSerializer(members, many=True).data,
                "groups": DatasetGroupRoleAssignmentSerializer(groups, many=True).data,
            }
        )


class DatasetRoleMemberListView(_DatasetAccessView):
    @swagger_auto_schema(
        operation_description="Grant this role on this data set to a user or service account",
        request_body=UserReferenceSerializer,
        manual_parameters=[DATA_SET_ID_PARAMETER, ROLE_ID_PARAMETER],
    )
    @global_permission_required(PERMISSIONS.DATA_SET_ROLE.ASSIGN)
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


class DatasetRoleMemberView(_DatasetAccessView):
    @swagger_auto_schema(
        operation_description="Revoke this role on this data set from a user or service account",
        manual_parameters=[
            DATA_SET_ID_PARAMETER,
            ROLE_ID_PARAMETER,
            openapi.Parameter("user_id", openapi.IN_PATH, description="ID of the user", type=openapi.TYPE_INTEGER),
        ],
    )
    @global_permission_required(PERMISSIONS.DATA_SET_ROLE.ASSIGN)
    def delete(self, request, data_set_id, role_id, user_id):
        data_set = self._get_dataset(data_set_id)
        assignment = get_object_or_404(
            DatasetUserRoleAssignment, user_id=user_id, dataset=data_set, role_id=role_id
        )
        assignment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DatasetRoleGroupListView(_DatasetAccessView):
    @swagger_auto_schema(
        operation_description="Grant this role on this data set to a group",
        request_body=GroupReferenceSerializer,
        manual_parameters=[DATA_SET_ID_PARAMETER, ROLE_ID_PARAMETER],
    )
    @global_permission_required(PERMISSIONS.DATA_SET_ROLE.ASSIGN)
    def post(self, request, data_set_id, role_id):
        """Granting to a group someone already holds this role through succeeds: the two grants
        are independent, and group membership can change tomorrow."""
        data_set, role = self._get_dataset_and_role(data_set_id, role_id)
        serializer = GroupReferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assignment, created = DatasetGroupRoleAssignment.objects.get_or_create(
            group=serializer.validated_data["group"], dataset=data_set, role=role
        )
        return Response(
            DatasetGroupRoleAssignmentSerializer(assignment).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class DatasetRoleGroupView(_DatasetAccessView):
    @swagger_auto_schema(
        operation_description="Revoke this role on this data set from a group",
        manual_parameters=[
            DATA_SET_ID_PARAMETER,
            ROLE_ID_PARAMETER,
            openapi.Parameter("group_id", openapi.IN_PATH, description="ID of the group", type=openapi.TYPE_INTEGER),
        ],
    )
    @global_permission_required(PERMISSIONS.DATA_SET_ROLE.ASSIGN)
    def delete(self, request, data_set_id, role_id, group_id):
        """Removes only this grant, even when the subjects behind it still hold the role another
        way. The client re-fetches, and the remaining path is visible in the response."""
        data_set = self._get_dataset(data_set_id)
        assignment = get_object_or_404(
            DatasetGroupRoleAssignment, group_id=group_id, dataset=data_set, role_id=role_id
        )
        assignment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
