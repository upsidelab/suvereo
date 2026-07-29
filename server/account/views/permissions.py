from django.contrib.auth.models import Permission
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import ListAPIView

from account.authorization import DATASET_PERMISSION_CODENAMES, GLOBAL_PERMISSION_CODENAMES
from account.permissions import IsApplicationAdmin
from account.serializers import PermissionOptionSerializer


class PermissionListView(ListAPIView):
    """List app-defined permissions eligible for role composition.

    Never returns Django's auto-generated per-model add_x/change_x/delete_x/view_x
    permissions — only the codenames explicitly named as constants in authorization.py.
    """

    permission_classes = [IsApplicationAdmin]
    serializer_class = PermissionOptionSerializer
    pagination_class = None

    @swagger_auto_schema(
        operation_description="List app-defined permissions for the role composer checklist",
        manual_parameters=[
            openapi.Parameter(
                "scope", openapi.IN_QUERY, description="'global' or 'dataset'", type=openapi.TYPE_STRING, required=True
            )
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        scope = self.request.query_params.get("scope")
        if scope == "global":
            codenames = GLOBAL_PERMISSION_CODENAMES
        elif scope == "dataset":
            codenames = DATASET_PERMISSION_CODENAMES
        else:
            return Permission.objects.none()
        bare_codenames = {c.split(".")[-1] for c in codenames}
        return Permission.objects.filter(codename__in=bare_codenames).select_related("content_type").order_by("codename")
