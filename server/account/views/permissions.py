from django.contrib.auth.models import Permission
from django.db.models import Q
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.authorization import (
    PERMISSION_ENTITIES,
    PERMISSION_SCOPES,
    PERMISSIONS,
    PUBLIC_CODES,
    any_global_permission_required,
    dependencies_within,
    entity_label,
    permission_label,
)
from account.serializers import PermissionEntitySerializer

DEFAULT_SCOPE = "global"


class PermissionListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List the permissions that can be granted, grouped by entity",
        manual_parameters=[
            openapi.Parameter(
                "scope",
                openapi.IN_QUERY,
                description=f"'global' or 'dataset'. Defaults to '{DEFAULT_SCOPE}'.",
                type=openapi.TYPE_STRING,
                required=False,
            )
        ],
        responses={200: PermissionEntitySerializer(many=True)},
    )
    @any_global_permission_required(PERMISSIONS.GLOBAL_ROLE.VIEW, PERMISSIONS.DATASET_ROLE.VIEW)
    def get(self, request):
        scope = request.query_params.get("scope", DEFAULT_SCOPE)
        if scope not in PERMISSION_SCOPES:
            return Response(
                {"scope": [f"Must be one of: {', '.join(PERMISSION_SCOPES)}."]},
                status=400,
            )

        in_scope = set(PERMISSION_SCOPES[scope])
        labels = self._labels_for(in_scope)
        requirements = self._requirements_for(PERMISSION_SCOPES[scope])

        entities = []
        for entity_name, permission_set in PERMISSION_ENTITIES.items():
            codenames = [codename for codename in permission_set if codename in in_scope]
            if not codenames:
                continue
            entities.append(
                {
                    "entity": entity_name.lower(),
                    "label": entity_label(entity_name),
                    "permissions": [
                        {
                            "code": PUBLIC_CODES[codename],
                            "label": labels.get(codename, PUBLIC_CODES[codename]),
                            "requires": requirements.get(PUBLIC_CODES[codename], []),
                        }
                        for codename in codenames
                    ],
                }
            )
        return Response(PermissionEntitySerializer(entities, many=True).data)

    def _requirements_for(self, scope_permissions) -> dict[str, list[str]]:
        """What each permission cannot be granted without, keyed by the permission and in public codes."""
        requirements: dict[str, list[str]] = {}
        for required, dependents in dependencies_within(scope_permissions).items():
            for dependent in dependents:
                requirements.setdefault(PUBLIC_CODES[dependent], []).append(PUBLIC_CODES[required])
        return {code: sorted(required) for code, required in requirements.items()}

    def _labels_for(self, codenames) -> dict[str, str]:
        """Django's own `Permission.name` ("Can add data set") is the label for now. Matched on
        (app_label, codename) pairs rather than bare codenames, so an unrelated permission on
        another model that happens to share a codename is never picked up."""
        query = Q()
        for codename in codenames:
            app_label, bare_codename = codename.split(".")
            query |= Q(content_type__app_label=app_label, codename=bare_codename)

        permissions = Permission.objects.filter(query).select_related("content_type")
        return {permission_label(permission): permission.name for permission in permissions}
