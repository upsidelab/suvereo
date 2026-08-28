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
from account.serializers import GroupReferenceSerializer, GroupSerializer

GLOBAL_ROLE_ID_PARAMETER = openapi.Parameter(
    "id", openapi.IN_PATH, description="ID of the global role", type=openapi.TYPE_INTEGER
)
GROUP_ID_PARAMETER = openapi.Parameter(
    "group_id", openapi.IN_PATH, description="ID of the group", type=openapi.TYPE_INTEGER
)


class GlobalRoleGroupListView(APIView):
    """List the groups holding a global role; grant it to one.

    The same grant is reachable from the group side at `/api/groups/<id>/global_roles`: a role's
    screen reads "who holds this" and a group's reads "what does this hold".
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List the groups holding a global role",
        manual_parameters=[GLOBAL_ROLE_ID_PARAMETER],
        responses={200: GroupSerializer(many=True)},
    )
    @global_permission_required(PERMISSIONS.GLOBAL_ROLE.VIEW)
    def get(self, request, id):
        global_role = get_object_or_404(GlobalRole, pk=id)
        groups = UserGroup.objects.with_counts().filter(global_roles=global_role).order_by("name")
        return Response(GroupSerializer(groups, many=True).data)

    @swagger_auto_schema(
        operation_description="Grant a global role to a group",
        request_body=GroupReferenceSerializer,
        manual_parameters=[GLOBAL_ROLE_ID_PARAMETER],
        responses={201: GroupSerializer},
    )
    @global_permission_required(PERMISSIONS.GLOBAL_ROLE.ASSIGN)
    def post(self, request, id):
        global_role = get_object_or_404(GlobalRole, pk=id)
        serializer = GroupReferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group = serializer.validated_data["group"]
        was_held = group.global_roles.filter(pk=global_role.pk).exists()
        if not was_held:
            group.global_roles.add(global_role)
        return Response(
            GroupSerializer(UserGroup.objects.with_counts().get(pk=group.pk)).data,
            status=status.HTTP_200_OK if was_held else status.HTTP_201_CREATED,
        )


class GlobalRoleGroupDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Revoke a global role from a group",
        manual_parameters=[GLOBAL_ROLE_ID_PARAMETER, GROUP_ID_PARAMETER],
    )
    @global_permission_required(PERMISSIONS.GLOBAL_ROLE.ASSIGN)
    def delete(self, request, id, group_id):
        global_role = get_object_or_404(GlobalRole, pk=id)
        group = get_object_or_404(UserGroup, pk=group_id)

        if not group.global_roles.filter(pk=global_role.pk).exists():
            raise Http404("No global role grant matches the given query.")
        group.global_roles.remove(global_role)
        return Response(status=status.HTTP_204_NO_CONTENT)
