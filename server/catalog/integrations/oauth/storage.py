"""Short-lived storage for OAuth handshakes that are still in flight."""

import hashlib

from django.core.cache import cache

from catalog.integrations.oauth.config import (
    CLIENT_LIFETIME_SECONDS,
    FLOW_LIFETIME_SECONDS,
    RESULT_LIFETIME_SECONDS,
)
from catalog.integrations.oauth.types import ClientCredentials, FlowResult, PendingFlow

_KEY_PREFIX = "integration-oauth-flow:"
_RESULT_PREFIX = "integration-oauth-result:"
_CLIENT_PREFIX = "integration-oauth-client:"


def _key(state: str) -> str:
    return f"{_KEY_PREFIX}{state}"


def _result_key(state: str) -> str:
    return f"{_RESULT_PREFIX}{state}"


def store_result(state: str, result: FlowResult) -> None:
    """Leave the outcome for the window that began the flow to collect."""
    cache.set(_result_key(state), result, timeout=RESULT_LIFETIME_SECONDS)


def read_result(state: str) -> FlowResult | None:
    """Look at the outcome for ``state`` without consuming it."""
    if not state:
        return None
    return cache.get(_result_key(state))


def discard_result(state: str) -> None:
    """Drop a collected outcome, so a credential is handed over once."""
    cache.delete(_result_key(state))


def _client_key(integration_type: str, target: str, redirect_uri: str) -> str:
    fingerprint = hashlib.sha256(f"{integration_type}|{target}|{redirect_uri}".encode()).hexdigest()
    return f"{_CLIENT_PREFIX}{fingerprint}"


def read_client(integration_type: str, target: str, redirect_uri: str) -> ClientCredentials | None:
    """Credentials from an earlier registration against this server, if we still hold them."""
    return cache.get(_client_key(integration_type, target, redirect_uri))


def store_client(integration_type: str, target: str, redirect_uri: str, client: ClientCredentials) -> None:
    """Keep a registration so pressing Connect again reuses it rather than making another."""
    if client.get("client_secret"):
        return
    cache.set(_client_key(integration_type, target, redirect_uri), client, timeout=CLIENT_LIFETIME_SECONDS)


def discard_client(integration_type: str, target: str, redirect_uri: str) -> None:
    """Forget a registration a provider has stopped honouring, so the next attempt remakes it."""
    cache.delete(_client_key(integration_type, target, redirect_uri))


def store(state: str, flow: PendingFlow) -> None:
    """Hold a begun flow until its callback arrives, or until it expires."""
    cache.set(_key(state), flow, timeout=FLOW_LIFETIME_SECONDS)


def pop(state: str) -> PendingFlow | None:
    """Take the flow for ``state``, if one is still current, removing it so a code cannot be replayed."""
    if not state:
        return None
    key = _key(state)
    flow = cache.get(key)
    if flow is not None:
        cache.delete(key)
    return flow