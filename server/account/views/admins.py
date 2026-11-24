from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from account.authorization import PERMISSIONS, global_permission_required
from account.models import User
from account.serializers import UserSummarySerializer


class AdminListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List the accounts holding admin",
        responses={200: UserSummarySerializer(many=True)},
    )
    @global_permission_required(PERMISSIONS.GLOBAL_ROLE.VIEW)
    def get(self, request: Request) -> Response:
        admins = User.objects.filter(is_superuser=True).order_by("email")
        return Response(UserSummarySerializer(admins, many=True).data)
