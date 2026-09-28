"""Views driving the OAuth handshake for integration types that advertise one.

The admin leaves for the provider and returns on a bare GET carrying no session of ours; the
``state`` the authorization server echoes is what ties the two requests together.

Nothing here knows about MCP - a plugin opts in with ``SUPPORTS_OAUTH`` plus
``oauth_start``/``oauth_finish``.
"""

import logging
from urllib.parse import quote

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import escape
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.authorization import PERMISSIONS, enforce_dataset_scoped_permission
from catalog.integrations import oauth_config, oauth_flows
from catalog.integrations.registry import IntegrationPluginRegistry
from catalog.models import DataSet

logger = logging.getLogger(__name__)

CALLBACK_URL_NAME = "integration-oauth-callback"

CLIENT_REJECTED_ERRORS = frozenset({"invalid_client", "unauthorized_client"})


def callback_uri(request) -> str:
    """The redirect URI, which must match byte for byte across registration, authorize and exchange."""
    path = reverse(CALLBACK_URL_NAME)
    if base := oauth_config.BASE_URL:
        return f"{base.rstrip('/')}{path}"
    return request.build_absolute_uri(path)


def _return_origin(request) -> str:
    """The one origin the callback may hand a credential back to."""
    origin = request.headers.get("Origin", "")
    return origin if origin in settings.CORS_ALLOWED_ORIGINS else ""


def _plugin_supporting_oauth(integration_type: str):
    plugin_class = IntegrationPluginRegistry().get_plugin_class_by_type(integration_type)
    if not getattr(plugin_class, "SUPPORTS_OAUTH", False):
        return None
    return plugin_class


class IntegrationOAuthStartView(APIView):
    """Begin the handshake and hand back the URL the admin's browser should open."""

    permission_classes = [IsAuthenticated]

    def post(self, request, data_set_id):
        data_set = get_object_or_404(DataSet, pk=data_set_id)
        enforce_dataset_scoped_permission(self, PERMISSIONS.INTEGRATION.ADD, data_set)

        integration_type = request.data.get("type")
        config = request.data.get("config") or {}
        try:
            plugin_class = _plugin_supporting_oauth(integration_type)
        except KeyError:
            return Response(
                {"detail": f"Unknown integration type '{integration_type}'."}, status=status.HTTP_400_BAD_REQUEST
            )
        if plugin_class is None:
            return Response(
                {"detail": f"'{integration_type}' does not support connecting with OAuth."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        redirect_uri = callback_uri(request)
        target = str(config.get(getattr(plugin_class, "OAUTH_FIELD", ""), ""))
        known_client = oauth_flows.read_client(integration_type, target, redirect_uri)

        try:
            authorization_url, pending = plugin_class.oauth_start(config, redirect_uri, known_client)
        except Exception as e:
            logger.info("OAuth start failed for %s: %s", integration_type, e)
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if issued := pending.get("client"):
            oauth_flows.store_client(integration_type, target, redirect_uri, issued)

        oauth_flows.store(
            pending["state"],
            {
                "integration_type": integration_type,
                "pending": pending,
                "origin": _return_origin(request),
                "user_id": request.user.pk,
                "client_key": [integration_type, target, redirect_uri],
            },
        )
        return Response(
            {
                "authorization_url": authorization_url,
                "state": pending["state"],
                "expires_in": oauth_config.FLOW_LIFETIME_SECONDS,
            }
        )


class IntegrationOAuthResultView(APIView):
    """Report the outcome of a flow to the window that began it.

    The popup cannot be trusted to hand the result back itself, so the form asks for it here.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        state = request.query_params.get("state") or ""
        result = oauth_flows.read_result(state)
        if result is None or result.get("user_id") != request.user.pk:
            return Response({"status": "pending"})

        oauth_flows.discard_result(state)
        return Response({"status": "ready", "config": result.get("config"), "error": result.get("error")})


COMPLETE_PATH = "/oauth/complete"


def _hand_back(state: str, origin: str) -> HttpResponse:
    """Return the popup to the frontend, which can then tell the form without any polling.

    Only the state travels in the URL - the credential itself is fetched over an authenticated
    request, never put somewhere a browser would keep it in history.
    """
    if not origin:
        return _message_page("Could not return to the app. Close this window and try again.")
    return HttpResponseRedirect(f"{origin}{COMPLETE_PATH}?state={quote(state)}")


def _message_page(text: str) -> HttpResponse:
    """Shown only when the popup cannot be sent back to the app it came from."""
    return HttpResponse(
        f"""<!doctype html>
<meta charset="utf-8">
<title>Connecting…</title>
<body style="font:14px system-ui;padding:2rem;color:#444"><p>{escape(text)}</p></body>"""
    )


class IntegrationOAuthCallbackView(APIView):
    """Receive the provider's redirect, exchange the code and pass the credentials back."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        state = request.query_params.get("state") or ""
        flow = oauth_flows.pop(state)
        if flow is None:
            return _message_page("This authorization has expired or was never started.")

        payload = self._outcome(request, flow)
        oauth_flows.store_result(state, {**payload, "user_id": flow["user_id"]})
        return _hand_back(state, flow["origin"])

    def _outcome(self, request, flow: dict) -> dict:
        if error := request.query_params.get("error"):
            if error in CLIENT_REJECTED_ERRORS:
                self._forget_registration(flow)
            return {"error": request.query_params.get("error_description") or error}

        code = request.query_params.get("code")
        if not code:
            return {"error": "The provider returned no authorization code."}

        try:
            plugin_class = _plugin_supporting_oauth(flow["integration_type"])
            return {"config": plugin_class.oauth_finish(flow["pending"], code)}
        except Exception as e:
            logger.info("OAuth callback failed for %s: %s", flow["integration_type"], e)
            self._forget_registration(flow)
            return {"error": str(e)}

    def _forget_registration(self, flow: dict) -> None:
        if key := flow.get("client_key"):
            oauth_flows.discard_client(*key)