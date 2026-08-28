from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.authorization import PERMISSIONS, global_permission_required
from account.models import GlobalRole, UserGroup
from account.serializers import GlobalRoleReferenceSerializer, GlobalRoleSerializer

GROUP_ID_PARAMETER = openapi.Parameter("id", openapi.IN_PATH, description="ID of the group", type=openapi.TYPE_INTEGER)
GLOBAL_ROLE_ID_PARAMETER = openapi.Parameter(
    "global_role_id", openapi.IN_PATH, description="ID of the global role", type=openapi.TYPE_INTEGER
)


class GroupGlobalRoleListView(APIView):
    """Grant a global role to a group."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Grant a global role to a group",
        request_body=GlobalRoleReferenceSerializer,
        manual_parameters=[GROUP_ID_PARAMETER],
        responses={201: GlobalRoleSerializer},
    )
    @global_permission_required(PERMISSIONS.GLOBAL_ROLE.ASSIGN)
    def post(self, request, id):
        group = get_object_or_404(UserGroup, pk=id)
        serializer = GlobalRoleReferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        global_role = serializer.validated_data["global_role"]
        was_held = group.global_roles.filter(pk=global_role.pk).exists()
        if not was_held:
            group.global_roles.add(global_role)
        return Response(
            GlobalRoleSerializer(global_role).data,
            status=status.HTTP_200_OK if was_held else status.HTTP_201_CREATED,
        )


class GroupGlobalRoleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Revoke a global role from a group",
        manual_parameters=[GROUP_ID_PARAMETER, GLOBAL_ROLE_ID_PARAMETER],
    )
    @global_permission_required(PERMISSIONS.GLOBAL_ROLE.ASSIGN)
    def delete(self, request, id, global_role_id):
        group = get_object_or_404(UserGroup, pk=id)
        global_role = get_object_or_404(GlobalRole, pk=global_role_id)

        if not group.global_roles.filter(pk=global_role.pk).exists():
            raise Http404("No global role grant matches the given query.")
        group.global_roles.remove(global_role)
        return Response(status=status.HTTP_204_NO_CONTENT)
