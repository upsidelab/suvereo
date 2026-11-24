from typing import Any

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import ListCreateAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from account.authorization import PERMISSIONS, global_permission_required
from account.models import User
from account.serializers import UserSerializer, UserUpdatePasswordSerializer, UserUpdateSerializer


class UserListView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    @swagger_auto_schema(operation_description="List all users", manual_parameters=[])
    @global_permission_required(PERMISSIONS.USER.VIEW)
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[User]:
        return User.objects.filter(is_service_account=False).order_by("email")

    @swagger_auto_schema(operation_description="Create a new user", request_body=UserSerializer)
    @global_permission_required(PERMISSIONS.USER.ADD)
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().post(request, *args, **kwargs)


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
    def get_object(self) -> User:
        return get_object_or_404(User, id=self.kwargs["id"], is_service_account=False)

    @global_permission_required(PERMISSIONS.USER.CHANGE)
    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().update(request, *args, **kwargs)


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
    def get_object(self) -> User:
        return get_object_or_404(User, id=self.kwargs["id"], is_service_account=False)

    @global_permission_required(PERMISSIONS.USER.CHANGE)
    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().update(request, *args, **kwargs)
