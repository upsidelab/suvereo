from django.conf import settings
from django.contrib.auth import authenticate
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.authentication import AUTH_TOKEN_COOKIE_NAME, HUMAN_TOKEN_LIFETIME
from account.models import AuthToken
from account.serializers import AccountSerializer


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes = []

    @swagger_auto_schema(
        operation_description="Login to obtain an authenticated auth-token cookie",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="Email"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, description="Password"),
            },
        ),
        responses={
            200: AccountSerializer,
            403: "Forbidden",
        },
    )
    def post(self, request):
        user = authenticate(username=request.data["email"], password=request.data["password"])
        if not user:
            return Response({}, status=403)

        token = AuthToken.objects.create(user=user, expires_at=timezone.now() + HUMAN_TOKEN_LIFETIME)
        get_token(request)

        response = Response(AccountSerializer(user).data)
        response.set_cookie(
            AUTH_TOKEN_COOKIE_NAME,
            token.key,
            max_age=int(HUMAN_TOKEN_LIFETIME.total_seconds()),
            httponly=True,
            secure=settings.AUTH_TOKEN_COOKIE_SECURE,
            samesite=settings.AUTH_TOKEN_COOKIE_SAMESITE,
        )
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(operation_description="Log out and invalidate the current auth token")
    def post(self, request):
        key = request.COOKIES.get(AUTH_TOKEN_COOKIE_NAME)
        if key:
            AuthToken.objects.filter(key=key).delete()
        response = Response(status=204)
        response.delete_cookie(AUTH_TOKEN_COOKIE_NAME)
        return response


class CsrfView(APIView):
    authentication_classes = []

    @swagger_auto_schema(operation_description="Ensure a CSRF cookie is set for the current browser")
    def get(self, request):
        get_token(request)
        return Response(status=204)
