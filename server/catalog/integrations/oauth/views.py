"""Views driving the OAuth handshake for any integration that implements ``BaseOAuthIntegration``."""

import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from suvereo_common.oauth import NoAuthorizationRequired
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from account.authorization import PERMISSIONS, enforce_any_dataset_scoped_permission, enforce_dataset_scoped_permission
from catalog.integrations.config_patch import merge_into_integration
from catalog.integrations.oauth import storage
from catalog.integrations.oauth.config import FLOW_LIFETIME_SECONDS
from catalog.integrations.oauth.helpers import (
    CLIENT_REJECTED_ERRORS,
    callback_uri,
    plugin_supporting_oauth,
    return_origin,
)
from catalog.integrations.oauth.responses import hand_back, message_page
from catalog.integrations.oauth.types import HandshakeOutcome, PendingFlow
from catalog.models import DataSet

logger = logging.getLogger(__name__)

#: Connecting a server both adds one and re-authorizes an existing one, so either right allows it.
CONNECT_PERMISSIONS = (PERMISSIONS.INTEGRATION.ADD, PERMISSIONS.INTEGRATION.CHANGE)


class IntegrationOAuthStartView(APIView):
    """Begin the handshake and hand back the URL the admin's browser should open."""

    permission_classes = [IsAuthenticated]

    def post(self, request, data_set_id):
        data_set = get_object_or_404(DataSet, pk=data_set_id)
        enforce_any_dataset_scoped_permission(self, data_set, *CONNECT_PERMISSIONS)

        integration_type = request.data.get("type")
        config = request.data.get("config") or {}
        try:
            plugin_class = plugin_supporting_oauth(integration_type)
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
        target = str(config.get(plugin_class.OAUTH_FIELD) or "").strip()
        known_client = storage.read_client(integration_type, target, redirect_uri)

        try:
            authorization = plugin_class.oauth_start(target, redirect_uri, known_client)
        except NoAuthorizationRequired as e:
            return Response({"authorization_required": False, "detail": str(e)})
        except Exception as e:
            logger.info("OAuth start failed for %s: %s", integration_type, e)
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        pending = authorization.pending
        storage.store_client(integration_type, target, redirect_uri, pending.client)

        storage.store(
            pending.state,
            {
                "integration_type": integration_type,
                "data_set_id": data_set.pk,
                "pending": pending,
                "origin": return_origin(request, settings.CORS_ALLOWED_ORIGINS),
                "user_id": request.user.pk,
                "client_key": [integration_type, target, redirect_uri],
            },
        )
        return Response(
            {
                "authorization_url": authorization.authorization_url,
                "state": pending.state,
                "expires_in": FLOW_LIFETIME_SECONDS,
            }
        )


class IntegrationOAuthRefreshView(APIView):
    """Renew a stored token on demand, without sending the admin through the provider again."""

    permission_classes = [IsAuthenticated]

    def post(self, request, data_set_id):
        data_set = get_object_or_404(DataSet, pk=data_set_id)
        enforce_dataset_scoped_permission(self, PERMISSIONS.INTEGRATION.CHANGE, data_set)

        integration_type = request.data.get("type")
        try:
            plugin_class = plugin_supporting_oauth(integration_type)
        except KeyError:
            return Response(
                {"detail": f"Unknown integration type '{integration_type}'."}, status=status.HTTP_400_BAD_REQUEST
            )
        if plugin_class is None:
            return Response(
                {"detail": f"'{integration_type}' cannot renew a token."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            renewed = plugin_class.oauth_refresh(request.data.get("config") or {})
        except Exception as e:
            logger.info("OAuth refresh failed for %s: %s", integration_type, e)
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        merge_into_integration(request.data.get("integration_id"), renewed, dataset=data_set)
        return Response({"config": renewed})


class IntegrationOAuthResultView(APIView):
    """Report the outcome of a flow to the window that began it."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        state = request.query_params.get("state") or ""
        result = storage.read_result(state)
        if result is None or result.get("user_id") != request.user.pk:
            return Response({"status": "pending"})

        # What is handed over is a credential, so the right to configure the data set is checked
        # again here - the account that began the flow may have lost it in the meantime.
        data_set = get_object_or_404(DataSet, pk=result["data_set_id"])
        enforce_any_dataset_scoped_permission(self, data_set, *CONNECT_PERMISSIONS)

        storage.discard_result(state)
        return Response({"status": "ready", "config": result.get("config"), "error": result.get("error")})


class IntegrationOAuthCallbackView(APIView):
    """Receive the provider's redirect, exchange the code and pass the credentials back."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        state = request.query_params.get("state") or ""
        flow = storage.pop(state)
        if flow is None:
            return message_page("This authorization has expired or was never started.")

        payload = self._outcome(request, flow)
        storage.store_result(state, {**payload, "user_id": flow["user_id"], "data_set_id": flow["data_set_id"]})
        return hand_back(state, flow["origin"])

    def _outcome(self, request, flow: PendingFlow) -> HandshakeOutcome:
        if error := request.query_params.get("error"):
            if error in CLIENT_REJECTED_ERRORS:
                self._forget_registration(flow)
            return {"error": request.query_params.get("error_description") or error}

        code = request.query_params.get("code")
        if not code:
            return {"error": "The provider returned no authorization code."}

        try:
            plugin_class = plugin_supporting_oauth(flow["integration_type"])
            return {"config": plugin_class.oauth_exchange_code(flow["pending"], code)}
        except Exception as e:
            logger.info("OAuth callback failed for %s: %s", flow["integration_type"], e)
            self._forget_registration(flow)
            return {"error": str(e)}

    def _forget_registration(self, flow: PendingFlow) -> None:
        if key := flow.get("client_key"):
            storage.discard_client(*key)
