from typing import Any

from drf_yasg.utils import swagger_auto_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenBlacklistView


class LogoutView(TokenBlacklistView):
    @swagger_auto_schema(
        operation_description="Revoke a refresh token",
        responses={
            200: "Refresh token revoked",
            401: "Refresh token invalid, expired or already revoked",
        },
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().post(request, *args, **kwargs)
