from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Suvereo API",
        default_version="v1.0",
        description="Documentation for Suvereo API",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("api/docs.<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path("api/docs/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("", include("catalog.urls")),
    path("", include("catalog.integrations.urls")),
    path("", include("catalog.task_status.urls")),
    path("", include("agent.urls")),
    path("", include("agent.agentic_execution.urls")),
    path("", include("agent.task_status.urls")),
    path("", include("account.urls")),
    # Entity records use a /datasets/<id>/<slug>/ catch-all, so include last.
    path("", include("catalog.entities.urls")),
]
