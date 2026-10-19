from drf_yasg.utils import swagger_auto_schema
from rest_framework_simplejwt import views as simplejwt_views

from account.serializers import RefreshTokenSerializer, TokenPairResponseSerializer


class TokenRefreshView(simplejwt_views.TokenRefreshView):
    serializer_class = RefreshTokenSerializer

    @swagger_auto_schema(
        operation_description="Exchange a refresh token for a new token pair; the old refresh token is revoked",
        responses={
            200: TokenPairResponseSerializer,
            401: "Refresh token invalid, expired or revoked",
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
