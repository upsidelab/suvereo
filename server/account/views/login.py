from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.serializers import AccountSerializer


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    @swagger_auto_schema(
        operation_description="Login to establish an authenticated session",
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
        if user:
            login(request, user)
            get_token(request)
            serializer = AccountSerializer(user)
            return Response(serializer.data)
        return Response({}, status=403)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(operation_description="Log out and invalidate the current session")
    def post(self, request):
        logout(request)
        return Response(status=204)


class CsrfView(APIView):
    @swagger_auto_schema(operation_description="Ensure a CSRF cookie is set for the current browser")
    def get(self, request):
        get_token(request)
        return Response(status=204)
