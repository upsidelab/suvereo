"""The one part of the OAuth flow that is particular to MCP: provoking the challenge."""

import json

from enthusiast_common.oauth import (
    AuthorizationServer,
    NoAuthorizationRequired,
    discover_from_challenge,
    request,
)


def discover(url: str) -> AuthorizationServer:
    """Walk from an MCP server URL to the authorization server behind it."""
    probe = request(
        "POST",
        url,
        headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
        content=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}),
    )
    if probe.status_code != 401:
        raise NoAuthorizationRequired("This server needs no token - it can be saved as it is.")
    return discover_from_challenge(url, probe.headers.get("WWW-Authenticate", ""))
