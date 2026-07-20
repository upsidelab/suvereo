"""
URL configuration for pecl project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="E-Commerce LLM API",
        default_version="v1.0",
        description=(
            "Documentation for E-Commerce LLM API. Browser clients authenticate via "
            "session cookie (log in through POST /api/auth/login, then send the "
            "X-CSRFToken header — read from the csrftoken cookie — on mutating "
            "requests) and cannot use the Token security scheme below. The Token "
            "scheme is for service accounts only."
        ),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("api/docs<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path("api/docs/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("admin/", admin.site.urls),
    path("", include("catalog.urls")),
    path("", include("catalog.integrations.urls")),
    path("", include("agent.urls")),
    path("", include("agent.agentic_execution.urls")),
    path("", include("account.urls")),
    # Entity records use a /datasets/<id>/<slug>/ catch-all, so include last.
    path("", include("catalog.entities.urls")),
]
