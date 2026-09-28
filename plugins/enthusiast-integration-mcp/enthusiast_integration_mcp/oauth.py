import base64
import hashlib
import ipaddress
import json
import re
import secrets
import socket
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx

# Required Notion, Asana, Atlassian, Sentry and PayPal all sit behind a WAF that
# answers 403 to non-browser clients, so discovery fails before any OAuth question is asked.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

TIMEOUT = 15.0

MAX_REDIRECTS = 5


class MCPOAuthError(Exception):
    """Raised when a server cannot be taken through the OAuth flow."""


@dataclass
class AuthorizationServer:
    """The endpoints an authorization server publishes, plus what the resource asks for."""

    authorization_endpoint: str
    token_endpoint: str
    registration_endpoint: str | None = None
    scopes: list[str] = field(default_factory=list)
    resource: str | None = None


def require_public_url(url: str) -> str:
    """Reject anything that would make the server fetch from its own network.

    The URL comes from a form, and everything here is fetched by the server rather than the
    browser, so without this an admin could read cloud metadata endpoints or internal services
    through it. Providers that need authorizing are public by nature, so nothing legitimate is
    lost - a server on a private address simply has no OAuth to discover.

    Returns:
        The URL, unchanged, when it is safe to fetch.

    Raises:
        MCPOAuthError: If the scheme is not HTTP(S), the host is unresolvable, or it resolves to
            an address that is not publicly routable.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise MCPOAuthError("Enter an http:// or https:// URL.")
    if not parsed.hostname:
        raise MCPOAuthError("That URL has no host.")

    try:
        resolved = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as e:
        raise MCPOAuthError(f"Could not resolve {parsed.hostname}.") from e

    for family, _, _, _, address in resolved:
        ip = ipaddress.ip_address(address[0])
        if not ip.is_global:
            raise MCPOAuthError(
                f"{parsed.hostname} resolves to a private address. Connect only works with servers "
                "reachable on the public internet."
            )
    return url


def _client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT, follow_redirects=False, headers={"User-Agent": USER_AGENT})


def _send(client: httpx.Client, method: str, url: str, **kwargs: Any) -> httpx.Response:
    """Make a request, following redirects one vetted hop at a time.

    Providers do redirect - a ``.well-known`` document served from a canonical host, say - so
    refusing outright would turn them away. Letting httpx follow them silently would instead let a
    public URL bounce the server onto its own network, so every hop is checked in turn.

    Raises:
        MCPOAuthError: If a hop fails the public-address check, or the chain does not settle.
    """
    for _ in range(MAX_REDIRECTS):
        response = client.request(method, require_public_url(url), **kwargs)
        if not response.is_redirect or not (location := response.headers.get("Location")):
            return response
        url = str(response.next_request.url) if response.next_request else location
        if response.status_code not in (307, 308):
            method, kwargs = "GET", {k: v for k, v in kwargs.items() if k == "headers"}
    raise MCPOAuthError("That server redirected too many times.")


def _get_json(client: httpx.Client, url: str) -> dict[str, Any]:
    response = _send(client, "GET", url, headers={"Accept": "application/json"})
    response.raise_for_status()
    return response.json()


def discover(url: str) -> AuthorizationServer:
    """Walk from an MCP server URL to the authorization server behind it.

    Args:
        url: The MCP endpoint the admin entered.

    Returns:
        The authorization server's endpoints and the scopes the resource asks for.

    Raises:
        MCPOAuthError: If the server needs no authorization, or publishes no usable metadata.
    """
    with _client() as client:
        probe = _send(
            client,
            "POST",
            url,
            headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
            content=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}),
        )
        if probe.status_code != 401:
            raise MCPOAuthError(
                f"This server did not ask for authorization (HTTP {probe.status_code}). "
                "Connect is only needed for servers that require a token."
            )

        challenge = probe.headers.get("WWW-Authenticate", "")
        scope_match = re.search(r'scope="([^"]+)"', challenge)
        scopes = scope_match.group(1).split() if scope_match else []
        resource_match = re.search(r'resource_metadata="([^"]+)"', challenge)
        resource = None
        issuers: list[str] = []

        if resource_match:
            try:
                resource_metadata = _get_json(client, resource_match.group(1))
                issuers = resource_metadata.get("authorization_servers") or []
                resource = resource_metadata.get("resource")
                scopes = scopes or resource_metadata.get("scopes_supported") or []
            except httpx.HTTPError:
                issuers = []

        origin = re.match(r"(https?://[^/]+)", url)
        if not issuers and origin:
            issuers = [origin.group(1)]

        for issuer in issuers:
            for well_known in ("/.well-known/oauth-authorization-server", "/.well-known/openid-configuration"):
                try:
                    metadata = _get_json(client, issuer.rstrip("/") + well_known)
                except httpx.HTTPError:
                    continue
                if "authorization_endpoint" not in metadata or "token_endpoint" not in metadata:
                    continue
                return AuthorizationServer(
                    authorization_endpoint=metadata["authorization_endpoint"],
                    token_endpoint=metadata["token_endpoint"],
                    registration_endpoint=metadata.get("registration_endpoint"),
                    scopes=scopes or metadata.get("scopes_supported") or [],
                    resource=resource,
                )

    raise MCPOAuthError(
        "This server requires authorization but publishes no OAuth metadata we can read. "
        "Paste a token manually instead."
    )


def register_client(server: AuthorizationServer, redirect_uri: str, client_name: str) -> dict[str, Any]:
    """Register this deployment as a client, so no app has to be created by hand.

    Returns:
        The credentials issued, holding at least ``client_id``.

    Raises:
        MCPOAuthError: If the server does not offer registration, or refuses it.
    """
    if not server.registration_endpoint:
        raise MCPOAuthError(
            "This server cannot register us automatically, so Connect does not work with it. "
            "Create a token in the provider's own settings and paste it into Auth token."
        )
    payload: dict[str, Any] = {
        "client_name": client_name,
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    if server.scopes:
        payload["scope"] = " ".join(server.scopes)

    with _client() as client:
        response = _send(client, "POST", server.registration_endpoint, json=payload)
    if response.status_code >= 400:
        raise MCPOAuthError(f"The server refused client registration (HTTP {response.status_code}).")
    credentials = response.json()
    if not credentials.get("client_id"):
        raise MCPOAuthError("The server registered a client but returned no client_id.")
    return credentials


def build_authorization_url(server: AuthorizationServer, client_id: str, redirect_uri: str) -> tuple[str, str, str]:
    """Build the URL the admin is sent to, with PKCE.

    Returns:
        The authorization URL, the PKCE verifier and the state; the callback must check both
        against what it receives.
    """
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_urlsafe(32)

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if server.scopes:
        params["scope"] = " ".join(server.scopes)
    if server.resource:
        params["resource"] = server.resource

    return f"{server.authorization_endpoint}?{urlencode(params)}", verifier, state


def exchange_code(
    token_endpoint: str,
    code: str,
    verifier: str,
    client_id: str,
    redirect_uri: str,
    client_secret: str | None = None,
    resource: str | None = None,
) -> dict[str, Any]:
    """Trade the authorization code for tokens.

    Raises:
        MCPOAuthError: If the server rejects the exchange.
    """
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": verifier,
    }
    if client_secret:
        data["client_secret"] = client_secret
    if resource:
        data["resource"] = resource

    with _client() as client:
        response = _send(client, "POST", token_endpoint, data=data, headers={"Accept": "application/json"})
    if response.status_code >= 400:
        raise MCPOAuthError(f"The server refused the token exchange (HTTP {response.status_code}).")
    tokens = response.json()
    if not tokens.get("access_token"):
        raise MCPOAuthError("The server completed the exchange but returned no access token.")
    return tokens