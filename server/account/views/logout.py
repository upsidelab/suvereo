from drf_yasg.utils import swagger_auto_schema
from rest_framework_simplejwt.views import TokenBlacklistView


class LogoutView(TokenBlacklistView):
    @swagger_auto_schema(
        operation_description="Revoke a refresh token",
        responses={
            200: "Refresh token revoked",
            401: "Refresh token invalid, expired or already revoked",
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
