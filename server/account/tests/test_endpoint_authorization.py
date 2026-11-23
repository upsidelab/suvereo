import inspect

import pytest
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

PROJECT_APPS = ("account.", "agent.", "catalog.", "utils.")
HANDLERS = ("get", "post", "put", "patch", "delete")
# Where a handler's check can live besides the handler: DRF's generic actions, which put and patch call
# through update, the querysets that scope lookups, and the result check of the task status views.
SCOPING_METHODS = (
    "list",
    "retrieve",
    "create",
    "update",
    "partial_update",
    "destroy",
    "get_queryset",
    "get_object",
    "_is_result_visible",
)

# Calls that authorize a request: the account.authorization decorators and helpers, the visibility
# querysets, and lookups bound to the requesting user.
AUTHORIZATION_MARKERS = (
    "permission_required",
    "any_permission_on_any_dataset_required",
    "admin_required",
    "enforce_",
    "has_dataset_perm",
    "has_any_",
    "datasets_with_permission",
    "visible_to",
    "permission_denied",
    "user=request.user",
    "user=self.request.user",
)

PUBLIC_VIEWS = {
    "account.views.login.LoginView": "signs a user in",
    "account.views.token_refresh.TokenRefreshView": "authenticated by the refresh token in the body",
    "account.views.logout.LogoutView": "authenticated by the refresh token in the body",
    "catalog.integrations.oauth.views.IntegrationOAuthCallbackView": "the provider redirects here; the state is checked",
}

# Views every authenticated user may call: they act on the user's own account or return no data-set content.
SELF_SCOPED_VIEWS = {
    "account.views.accounts.AccountView": "the requesting user's account",
    "account.views.ws_ticket.WebSocketTicketView": "issues a ticket for the requesting user",
    "agent.conversation.views.SupportedFileTypesView": "lists supported file extensions",
}


def project_views() -> list[type[APIView]]:
    views = set()

    def walk(patterns: list) -> None:
        for pattern in patterns:
            if isinstance(pattern, URLResolver):
                walk(pattern.url_patterns)
            elif isinstance(pattern, URLPattern):
                view = getattr(pattern.callback, "cls", None)
                if view and view.__module__.startswith(PROJECT_APPS):
                    views.add(view)

    walk(get_resolver().url_patterns)
    return sorted(views, key=qualified_name)


def qualified_name(view: type) -> str:
    return f"{view.__module__}.{view.__name__}"


def project_source(view: type, method_name: str) -> str:
    for cls in view.__mro__:
        if method_name in vars(cls):
            if not cls.__module__.startswith(PROJECT_APPS):
                return ""
            return inspect.getsource(vars(cls)[method_name])
    return ""


@pytest.mark.parametrize("view", project_views(), ids=qualified_name)
def test_endpoint_requires_authentication(view: type[APIView]) -> None:
    if qualified_name(view) in PUBLIC_VIEWS:
        return
    assert any(issubclass(permission, IsAuthenticated) for permission in view.permission_classes), (
        f"{qualified_name(view)} must set permission_classes = [IsAuthenticated], see server/AGENTS.md#authorization"
    )


@pytest.mark.parametrize("view", project_views(), ids=qualified_name)
def test_endpoint_checks_a_permission(view: type[APIView]) -> None:
    name = qualified_name(view)
    if name in PUBLIC_VIEWS or name in SELF_SCOPED_VIEWS:
        return
    scoping = "".join(project_source(view, method) for method in SCOPING_METHODS)
    for handler in HANDLERS:
        if not hasattr(view, handler):
            continue
        source = project_source(view, handler) + scoping
        assert any(marker in source for marker in AUTHORIZATION_MARKERS), (
            f"{name}.{handler} has no permission check: use an account.authorization decorator, "
            "enforce_dataset_scoped_permission or a visibility queryset, see server/AGENTS.md#authorization"
        )
