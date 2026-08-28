from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.authorization import PERMISSIONS, global_permission_required
from account.models import GlobalRole, User
from account.serializers import UserReferenceSerializer, UserSummarySerializer

GLOBAL_ROLE_ID_PARAMETER = openapi.Parameter("id", openapi.IN_PATH, description="ID of the global role", type=openapi.TYPE_INTEGER)
USER_ID_PARAMETER = openapi.Parameter("user_id", openapi.IN_PATH, description="ID of the user", type=openapi.TYPE_INTEGER)


class GlobalRoleMemberListView(APIView):
    """List a global role's members; add a user to it."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List a global role's members",
        manual_parameters=[GLOBAL_ROLE_ID_PARAMETER],
        responses={200: UserSummarySerializer(many=True)},
    )
    @global_permission_required(PERMISSIONS.GLOBAL_ROLE.VIEW)
    def get(self, request, id):
        global_role = get_object_or_404(GlobalRole, pk=id)
        members = global_role.members.order_by("email")
        return Response(UserSummarySerializer(members, many=True).data)

    @swagger_auto_schema(
        operation_description="Add a user to a global role",
        request_body=UserReferenceSerializer,
        manual_parameters=[GLOBAL_ROLE_ID_PARAMETER],
    )
    @global_permission_required(PERMISSIONS.GLOBAL_ROLE.ASSIGN)
    def post(self, request, id):
        global_role = get_object_or_404(GlobalRole, pk=id)
        serializer = UserReferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        was_member = global_role.members.filter(pk=user.pk).exists()
        if not was_member:
            global_role.members.add(user)
        return Response(
            UserSummarySerializer(user).data,
            status=status.HTTP_200_OK if was_member else status.HTTP_201_CREATED,
        )


class GlobalRoleMemberDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Remove a user from a global role",
        manual_parameters=[GLOBAL_ROLE_ID_PARAMETER, USER_ID_PARAMETER],
    )
    @global_permission_required(PERMISSIONS.GLOBAL_ROLE.ASSIGN)
    def delete(self, request, id, user_id):
        global_role = get_object_or_404(GlobalRole, pk=id)
        user = get_object_or_404(User, pk=user_id)

        if not global_role.members.filter(pk=user.pk).exists():
            raise Http404("No global role membership matches the given query.")
        global_role.members.remove(user)
        return Response(status=status.HTTP_204_NO_CONTENT)
