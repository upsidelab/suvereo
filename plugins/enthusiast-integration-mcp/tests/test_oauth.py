from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from enthusiast_integration_mcp.integration import MCPServerIntegration
from enthusiast_integration_mcp.oauth import (
    AuthorizationServer,
    MCPOAuthError,
    build_authorization_url,
    discover,
    exchange_code,
    register_client,
)

REDIRECT = "https://enthusiast.example.com/api/integrations/oauth/callback/"

CHALLENGE = 'Bearer realm="OAuth", resource_metadata="https://srv.example.com/.well-known/oauth-protected-resource/mcp", scope="read write"'
RESOURCE_METADATA = {"resource": "https://srv.example.com/mcp", "authorization_servers": ["https://srv.example.com"]}
AS_METADATA = {
    "authorization_endpoint": "https://srv.example.com/authorize",
    "token_endpoint": "https://srv.example.com/token",
    "registration_endpoint": "https://srv.example.com/register",
}


def _response(status_code=200, json_body=None, headers=None):
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.headers = headers or {}
    response.json.return_value = json_body or {}
    response.raise_for_status.return_value = None
    return response


def _client_returning(post=None, gets=None):
    """A stand-in httpx client whose GETs are served in order from `gets`."""
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.post.return_value = post or _response()
    client.get.side_effect = list(gets or [])
    return client


class TestDiscover:
    def test_walks_the_challenge_to_the_authorization_server(self):
        client = _client_returning(
            post=_response(401, headers={"WWW-Authenticate": CHALLENGE}),
            gets=[_response(json_body=RESOURCE_METADATA), _response(json_body=AS_METADATA)],
        )

        with patch("enthusiast_integration_mcp.oauth._client", return_value=client):
            server = discover("https://srv.example.com/mcp")

        assert server.authorization_endpoint == "https://srv.example.com/authorize"
        assert server.token_endpoint == "https://srv.example.com/token"
        assert server.registration_endpoint == "https://srv.example.com/register"
        assert server.scopes == ["read", "write"]
        assert server.resource == "https://srv.example.com/mcp"

    def test_a_server_needing_no_token_is_reported_rather_than_guessed_at(self):
        client = _client_returning(post=_response(200))

        with patch("enthusiast_integration_mcp.oauth._client", return_value=client):
            with pytest.raises(MCPOAuthError, match="did not ask for authorization"):
                discover("https://open.example.com/mcp")

    def test_falls_back_to_the_origin_when_no_resource_metadata_is_published(self):
        client = _client_returning(
            post=_response(401, headers={"WWW-Authenticate": 'Bearer realm="OAuth"'}),
            gets=[_response(json_body=AS_METADATA)],
        )

        with patch("enthusiast_integration_mcp.oauth._client", return_value=client):
            server = discover("https://srv.example.com/mcp")

        assert server.token_endpoint == "https://srv.example.com/token"

    def test_unreadable_metadata_raises_rather_than_returning_a_half_built_server(self):
        client = _client_returning(
            post=_response(401, headers={"WWW-Authenticate": CHALLENGE}),
            gets=[httpx.ConnectError("boom"), httpx.ConnectError("boom"), httpx.ConnectError("boom")],
        )

        with patch("enthusiast_integration_mcp.oauth._client", return_value=client):
            with pytest.raises(MCPOAuthError, match="publishes no OAuth metadata"):
                discover("https://srv.example.com/mcp")


class TestRegisterClient:
    def test_registers_as_a_public_client_for_the_callback(self):
        client = _client_returning(post=_response(201, {"client_id": "abc123"}))
        server = AuthorizationServer("https://a/authorize", "https://a/token", "https://a/register", ["read"])

        with patch("enthusiast_integration_mcp.oauth._client", return_value=client):
            credentials = register_client(server, REDIRECT, "Enthusiast")

        assert credentials["client_id"] == "abc123"
        payload = client.post.call_args.kwargs["json"]
        assert payload["redirect_uris"] == [REDIRECT]
        assert payload["token_endpoint_auth_method"] == "none"
        assert "refresh_token" in payload["grant_types"]

    def test_a_server_without_registration_points_at_the_manual_field(self):
        """Such a server still takes a token the admin can make themselves, so say that."""
        server = AuthorizationServer("https://a/authorize", "https://a/token", registration_endpoint=None)

        with pytest.raises(MCPOAuthError, match="paste it into Auth token"):
            register_client(server, REDIRECT, "Enthusiast")


class TestBuildAuthorizationUrl:
    def test_sends_pkce_and_the_resource(self):
        server = AuthorizationServer(
            "https://a/authorize", "https://a/token", scopes=["read"], resource="https://srv/mcp"
        )

        url, verifier, state = build_authorization_url(server, "abc123", REDIRECT)
        params = parse_qs(urlparse(url).query)

        assert params["code_challenge_method"] == ["S256"]
        assert params["client_id"] == ["abc123"]
        assert params["redirect_uri"] == [REDIRECT]
        assert params["state"] == [state]
        assert params["resource"] == ["https://srv/mcp"]
        assert params["code_challenge"][0] != verifier

    def test_each_call_is_unique_so_two_flows_cannot_collide(self):
        server = AuthorizationServer("https://a/authorize", "https://a/token")

        _, first_verifier, first_state = build_authorization_url(server, "abc", REDIRECT)
        _, second_verifier, second_state = build_authorization_url(server, "abc", REDIRECT)

        assert first_verifier != second_verifier
        assert first_state != second_state


class TestExchangeCode:
    def test_posts_the_verifier_and_returns_the_tokens(self):
        client = _client_returning(post=_response(200, {"access_token": "tok", "token_type": "bearer"}))

        with patch("enthusiast_integration_mcp.oauth._client", return_value=client):
            tokens = exchange_code("https://a/token", "code-1", "verifier-1", "abc123", REDIRECT)

        assert tokens["access_token"] == "tok"
        sent = client.post.call_args.kwargs["data"]
        assert sent["code_verifier"] == "verifier-1"
        assert sent["grant_type"] == "authorization_code"
        assert sent["redirect_uri"] == REDIRECT

    def test_a_refused_exchange_raises(self):
        client = _client_returning(post=_response(400, {"error": "invalid_grant"}))

        with patch("enthusiast_integration_mcp.oauth._client", return_value=client):
            with pytest.raises(MCPOAuthError, match="refused the token exchange"):
                exchange_code("https://a/token", "code-1", "verifier-1", "abc123", REDIRECT)


class TestIntegrationOAuthHooks:
    def test_oauth_start_needs_a_url(self):
        with pytest.raises(MCPOAuthError, match="Enter the server URL"):
            MCPServerIntegration.oauth_start({}, REDIRECT)

    def test_oauth_start_returns_the_state_the_callback_needs(self):
        server = AuthorizationServer("https://a/authorize", "https://a/token", "https://a/register")

        with (
            patch("enthusiast_integration_mcp.integration.discover", return_value=server),
            patch("enthusiast_integration_mcp.integration.register_client", return_value={"client_id": "abc"}),
        ):
            url, pending = MCPServerIntegration.oauth_start({"url": "https://srv/mcp"}, REDIRECT)

        assert url.startswith("https://a/authorize")
        assert pending["client_id"] == "abc"
        assert pending["token_endpoint"] == "https://a/token"
        assert pending["redirect_uri"] == REDIRECT
        assert pending["verifier"] and pending["state"]

    def test_oauth_finish_fills_the_auth_fields_the_form_already_has(self):
        pending = {
            "token_endpoint": "https://a/token",
            "verifier": "v",
            "client_id": "abc",
            "redirect_uri": REDIRECT,
        }

        with patch(
            "enthusiast_integration_mcp.integration.exchange_code",
            return_value={"access_token": "tok", "token_type": "bearer"},
        ):
            config = MCPServerIntegration.oauth_finish(pending, "code-1")

        assert config == {"auth_header": "Authorization", "auth_token": "Bearer tok"}