from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import ListCreateAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated

from account.authorization import PERMISSIONS, global_permission_required
from account.models import User
from account.serializers import UserSerializer, UserUpdatePasswordSerializer, UserUpdateSerializer


class UserListView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    @swagger_auto_schema(operation_description="List all users", manual_parameters=[])
    @global_permission_required(PERMISSIONS.USER.VIEW)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return User.objects.filter(is_service_account=False)

    @swagger_auto_schema(operation_description="Create a new user", request_body=UserSerializer)
    @global_permission_required(PERMISSIONS.USER.ADD)
    def perform_create(self, serializer):
        serializer.save()


class UserView(UpdateAPIView):
    permission_classes = [IsAuthenticated]
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

    @global_permission_required(PERMISSIONS.USER.CHANGE)
    def perform_update(self, serializer):
        serializer.save()


class UserPasswordView(UpdateAPIView):
    permission_classes = [IsAuthenticated]
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

    @global_permission_required(PERMISSIONS.USER.CHANGE)
    def perform_update(self, serializer):
        serializer.save()
