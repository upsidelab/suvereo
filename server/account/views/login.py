from drf_yasg.utils import swagger_auto_schema
from rest_framework_simplejwt.views import TokenObtainPairView

from account.serializers import TokenPairResponseSerializer


class LoginView(TokenObtainPairView):
    @swagger_auto_schema(
        operation_description="Log in to obtain an access and refresh token pair",
        responses={
            200: TokenPairResponseSerializer,
            401: "Invalid credentials",
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
