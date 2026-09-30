"""Turning an approved authorization into a token."""

import base64
import hashlib
import secrets
from urllib.parse import urlencode

from . import http
from .discovery import AuthorizationServer
from .errors import OAuthError
from .types import OAuthTokens


def build_authorization_url(server: AuthorizationServer, client_id: str, redirect_uri: str) -> tuple[str, str, str]:
    """Build the URL the admin is sent to, with PKCE."""
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
    scopes = list(server.scopes)
    # Some servers only issue a refresh token when asked, and omit it from the resource scopes.
    if server.offers_offline_access and "offline_access" not in scopes:
        scopes.append("offline_access")
    if scopes:
        params["scope"] = " ".join(scopes)
    if server.resource:
        params["resource"] = server.resource

    return f"{server.authorization_endpoint}?{urlencode(params)}", verifier, state


def _request_tokens(token_endpoint: str, data: dict[str, str], refusal: str) -> OAuthTokens:
    """Ask the token endpoint for tokens, and insist on getting something usable back."""
    with http.open_client() as client:
        response = http.send(client, "POST", token_endpoint, data=data, headers={"Accept": "application/json"})
    if response.status_code >= 400:
        raise OAuthError(f"{refusal} (HTTP {response.status_code}).")
    tokens = response.json()
    if not tokens.get("access_token"):
        raise OAuthError("The server answered without an access token.")
    return OAuthTokens.model_validate(tokens)


def refresh_tokens(token_endpoint: str, refresh_token: str, client_id: str) -> OAuthTokens:
    """Trade a refresh token for a fresh access token."""
    return _request_tokens(
        token_endpoint,
        {"grant_type": "refresh_token", "refresh_token": refresh_token, "client_id": client_id},
        "This server would not renew its token, so it has to be connected again",
    )


def exchange_code(
    token_endpoint: str,
    code: str,
    verifier: str,
    client_id: str,
    redirect_uri: str,
    client_secret: str | None = None,
    resource: str | None = None,
) -> OAuthTokens:
    """Trade the authorization code for tokens."""
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
    return _request_tokens(token_endpoint, data, "The server refused the token exchange")
