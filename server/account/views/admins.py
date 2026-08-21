from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.authorization import PERMISSIONS, global_permission_required
from account.models import User
from account.serializers import UserSummarySerializer


class AdminListView(APIView):
    """Who holds admin.

    Admin is not a `Group` - it is a flag on the account (`is_superuser`), deliberately not grantable
    through any permission code. It is still a named set of accounts holding a set of capabilities, so
    a `global_role.view` holder has the same reason to read it as to read any global role's membership, and no
    `/api/global_roles/<id>/members` route can serve it. Hence this endpoint, gated on the same `group.view`.

    Read-only: granting and revoking admin stays on the user and service-account endpoints, where only
    an admin can write `is_admin`.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List the accounts holding admin",
        responses={200: UserSummarySerializer(many=True)},
    )
    @global_permission_required(PERMISSIONS.GLOBAL_ROLE.VIEW)
    def get(self, request):
        admins = User.objects.filter(is_superuser=True).order_by("email")
        return Response(UserSummarySerializer(admins, many=True).data)
