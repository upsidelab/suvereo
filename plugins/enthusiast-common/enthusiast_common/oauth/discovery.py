"""Finding the authorization server behind a protected resource, and registering with it."""

import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from . import http
from .errors import OAuthError


@dataclass
class AuthorizationServer:
    """The endpoints an authorization server publishes, plus what the resource asks for."""

    authorization_endpoint: str
    token_endpoint: str
    registration_endpoint: str | None = None
    scopes: list[str] = field(default_factory=list)
    resource: str | None = None


def register_client(server: AuthorizationServer, redirect_uri: str, client_name: str) -> dict[str, Any]:
    """Register this deployment as a client, so no app has to be created by hand."""
    if not server.registration_endpoint:
        raise OAuthError(
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

    with http.open_client() as client:
        response = http.send(client, "POST", server.registration_endpoint, json=payload)
    if response.status_code >= 400:
        raise OAuthError(f"The server refused client registration (HTTP {response.status_code}).")
    credentials = response.json()
    if not credentials.get("client_id"):
        raise OAuthError("The server registered a client but returned no client_id.")
    return credentials


def discover_from_challenge(resource_url: str, challenge: str) -> AuthorizationServer:
    """Walk from a ``WWW-Authenticate`` challenge to the authorization server behind the resource."""
    with http.open_client() as client:
        scope_match = re.search(r'scope="([^"]+)"', challenge)
        scopes = scope_match.group(1).split() if scope_match else []
        resource_match = re.search(r'resource_metadata="([^"]+)"', challenge)
        resource = None
        issuers: list[str] = []

        if resource_match:
            try:
                resource_metadata = http.get_json(client, resource_match.group(1))
                issuers = resource_metadata.get("authorization_servers") or []
                resource = resource_metadata.get("resource")
                scopes = scopes or resource_metadata.get("scopes_supported") or []
            except httpx.HTTPError:
                issuers = []

        origin = re.match(r"(https?://[^/]+)", resource_url)
        if not issuers and origin:
            issuers = [origin.group(1)]

        for issuer in issuers:
            for well_known in ("/.well-known/oauth-authorization-server", "/.well-known/openid-configuration"):
                try:
                    metadata = http.get_json(client, issuer.rstrip("/") + well_known)
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

    raise OAuthError(
        "This server requires authorization but publishes no OAuth metadata we can read. "
        "Paste a token manually instead."
    )
