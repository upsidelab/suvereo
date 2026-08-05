from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from account.authorization import ADMIN_GROUP_NAME, assert_not_self_removing_from_group
from account.models import User
from account.permissions import IsApplicationAdmin
from account.serializers import GroupDetailSerializer, GroupMemberSerializer, GroupSerializer


class GroupListView(ListCreateAPIView):
    """List every Django Group; create a new one (name + global permission_ids)."""

    permission_classes = [IsApplicationAdmin]
    queryset = Group.objects.all().order_by("name")
    pagination_class = None

    def get_serializer_class(self):
        if self.request.method == "POST":
            return GroupDetailSerializer
        return GroupSerializer

    @swagger_auto_schema(operation_description="List all groups")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(operation_description="Create a new group", request_body=GroupDetailSerializer)
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class GroupDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve/update a group's name and permissions; delete it (blocked for Admin)."""

    permission_classes = [IsApplicationAdmin]
    serializer_class = GroupDetailSerializer
    queryset = Group.objects.all()
    lookup_url_kwarg = "group_id"

    @swagger_auto_schema(operation_description="Retrieve a group")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(operation_description="Update a group's name/permissions", request_body=GroupDetailSerializer)
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(operation_description="Delete a group (the Admin group cannot be deleted)")
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.name == ADMIN_GROUP_NAME:
            return Response({"detail": "The Admin group cannot be deleted."}, status=status.HTTP_400_BAD_REQUEST)
        return super().delete(request, *args, **kwargs)


class GroupMembersView(GenericAPIView):
    permission_classes = [IsApplicationAdmin]
    serializer_class = GroupMemberSerializer

    @swagger_auto_schema(operation_description="List a group's members")
    def get(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id)
        serializer = GroupMemberSerializer(group.user_set.order_by("email"), many=True)
        return Response(serializer.data)

    @swagger_auto_schema(operation_description="Add a user to a group")
    def post(self, request, group_id):
        group = get_object_or_404(Group, pk=group_id)
        try:
            user = get_object_or_404(User, pk=request.data.get("user_id"))
        except (TypeError, ValueError):
            return Response({"detail": "user_id must be a valid integer."}, status=status.HTTP_400_BAD_REQUEST)
        user.groups.add(group)
        return Response(status=status.HTTP_201_CREATED)


class GroupMemberDetailView(APIView):
    permission_classes = [IsApplicationAdmin]

    @swagger_auto_schema(operation_description="Remove a user from a group")
    def delete(self, request, group_id, user_id):
        group = get_object_or_404(Group, pk=group_id)
        user = get_object_or_404(User, pk=user_id)
        try:
            assert_not_self_removing_from_group(request.user, user, group)
        except DjangoValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        user.groups.remove(group)
        return Response(status=status.HTTP_204_NO_CONTENT)
