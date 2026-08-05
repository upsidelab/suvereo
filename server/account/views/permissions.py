from django.contrib.auth.models import Permission
from django.db.models import Q
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
        # Match on (app_label, codename) pairs, not bare codename alone. A bare-codename
        # match would also return any unrelated permission on a different model that happens
        # to share the same codename (e.g. a stale/orphaned row left over from an abandoned
        # Meta.permissions declaration elsewhere).
        query = Q()
        for codename in codenames:
            app_label, bare_codename = codename.split(".", 1)
            query |= Q(content_type__app_label=app_label, codename=bare_codename)
        permissions = Permission.objects.filter(query).select_related(
            "content_type", "description_entry", "description_entry__implied_view_permission__content_type"
        )
        # codenames' own order is the intended display order (manage_X right before the view_X it implies)
        order_index = {codename: position for position, codename in enumerate(codenames)}
        return sorted(permissions, key=lambda p: order_index[f"{p.content_type.app_label}.{p.codename}"])
