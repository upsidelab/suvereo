"""Short-lived storage for OAuth handshakes that are still in flight.

One request begins a flow and another finishes it, possibly on a different worker, so the state
lives in the shared cache. Its TTL is what expires an abandoned flow.
"""

from typing import Any

from django.core.cache import cache

from catalog.integrations.oauth_config import FLOW_LIFETIME_SECONDS, RESULT_LIFETIME_SECONDS

_KEY_PREFIX = "integration-oauth-flow:"
_RESULT_PREFIX = "integration-oauth-result:"


def _key(state: str) -> str:
    return f"{_KEY_PREFIX}{state}"


def _result_key(state: str) -> str:
    return f"{_RESULT_PREFIX}{state}"


def store_result(state: str, result: dict[str, Any]) -> None:
    """Leave the outcome for the window that began the flow to collect.

    The popup cannot be relied on to hand it back directly: a provider may sever ``window.opener``
    on its own pages, and the browser never restores it.
    """
    cache.set(_result_key(state), result, timeout=RESULT_LIFETIME_SECONDS)


def pop_result(state: str) -> dict[str, Any] | None:
    """Take the outcome for ``state``, if the callback has stored one yet."""
    if not state:
        return None
    key = _result_key(state)
    result = cache.get(key)
    if result is not None:
        cache.delete(key)
    return result


def store(state: str, flow: dict[str, Any]) -> None:
    """Hold a begun flow until its callback arrives, or until it expires."""
    cache.set(_key(state), flow, timeout=FLOW_LIFETIME_SECONDS)


def pop(state: str) -> dict[str, Any] | None:
    """Take the flow for ``state``, if one is still current, removing it so a code cannot be replayed."""
    if not state:
        return None
    key = _key(state)
    flow = cache.get(key)
    if flow is not None:
        cache.delete(key)
    return flow