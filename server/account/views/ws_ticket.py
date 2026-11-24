from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from account.services.ws_tickets import WebSocketTicketService


class WebSocketTicketView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Issue a single-use ticket to pass as the `ticket` query param when opening a WebSocket",
        responses={
            201: openapi.Schema(
                type=openapi.TYPE_OBJECT, properties={"ticket": openapi.Schema(type=openapi.TYPE_STRING)}
            )
        },
    )
    def post(self, request: Request) -> Response:
        ticket = WebSocketTicketService().issue(request.user)
        return Response({"ticket": ticket}, status=status.HTTP_201_CREATED)
