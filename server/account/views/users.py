from django.contrib.auth.models import Group
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import ListCreateAPIView, UpdateAPIView
from rest_framework.response import Response

from account.authorization import PERM_MANAGE_USERS
from account.models import User
from account.permissions import HasRequiredPermission
from account.serializers import UserCreateSerializer, UserSerializer, UserUpdatePasswordSerializer, UserUpdateSerializer


class UserListView(ListCreateAPIView):
    permission_classes = [HasRequiredPermission]
    required_permission = PERM_MANAGE_USERS

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserCreateSerializer
        return UserSerializer

    @swagger_auto_schema(operation_description="List all users", manual_parameters=[])
    def get_queryset(self):
        return User.objects.filter(is_service_account=False)

    @swagger_auto_schema(operation_description="Create a new user", request_body=UserCreateSerializer)
    def perform_create(self, serializer):
        user = User.objects.create_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            is_active=serializer.validated_data["is_active"],
        )
        user.groups.set(Group.objects.filter(pk__in=serializer.validated_data["group_ids"]))


class UserView(UpdateAPIView):
    permission_classes = [HasRequiredPermission]
    required_permission = PERM_MANAGE_USERS
    serializer_class = UserUpdateSerializer

    @swagger_auto_schema(
        operation_description="Update a user",
        request_body=UserUpdateSerializer,
        manual_parameters=[
            openapi.Parameter("id", openapi.IN_PATH, description="ID of the user", type=openapi.TYPE_INTEGER)
        ],
    )
    def get_object(self):
        return User.objects.get(id=self.kwargs["id"], is_service_account=False)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = self.perform_update(serializer)
        return Response(UserSerializer(user).data)

    def perform_update(self, serializer):
        user = self.get_object()
        user.email = serializer.validated_data["email"]
        user.is_active = serializer.validated_data["is_active"]
        user.save()
        user.groups.set(Group.objects.filter(pk__in=serializer.validated_data["group_ids"]))
        return user


class UserPasswordView(UpdateAPIView):
    permission_classes = [HasRequiredPermission]
    required_permission = PERM_MANAGE_USERS
    serializer_class = UserUpdatePasswordSerializer

    @swagger_auto_schema(
        operation_description="Update a user's password",
        request_body=UserUpdatePasswordSerializer,
        manual_parameters=[
            openapi.Parameter("id", openapi.IN_PATH, description="ID of the user", type=openapi.TYPE_INTEGER)
        ],
    )
    def get_object(self):
        return User.objects.get(id=self.kwargs["id"], is_service_account=False)

    def perform_update(self, serializer):
        user = self.get_object()
        user.set_password(serializer.validated_data["password"])
        user.save()
