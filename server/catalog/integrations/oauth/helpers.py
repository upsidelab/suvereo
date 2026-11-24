from django.urls import reverse
from suvereo_common.integrations import BaseOAuthIntegration

from catalog.integrations.oauth import config
from catalog.integrations.registry import IntegrationPluginRegistry

CALLBACK_URL_NAME = "integration-oauth-callback"

CLIENT_REJECTED_ERRORS = frozenset({"invalid_client", "unauthorized_client"})


def callback_uri(request) -> str:
    path = reverse(CALLBACK_URL_NAME)
    if base := config.BASE_URL:
        return f"{base.rstrip('/')}{path}"
    return request.build_absolute_uri(path)


def return_origin(request, allowed: list[str]) -> str:
    origin = request.headers.get("Origin", "")
    return origin if origin in allowed else ""


def plugin_supporting_oauth(integration_type: str) -> type[BaseOAuthIntegration] | None:
    plugin_class = IntegrationPluginRegistry().get_plugin_class_by_type(integration_type)
    if not issubclass(plugin_class, BaseOAuthIntegration):
        return None
    return plugin_class
