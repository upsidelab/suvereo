import ipaddress
import socket
from unittest.mock import MagicMock, patch

import httpx
import pytest
from enthusiast_common.oauth import AuthorizationServer, OAuthError
from enthusiast_integration_mcp.integration import MCPServerIntegration
from enthusiast_integration_mcp.oauth import discover

REDIRECT = "https://enthusiast.example.com/api/integrations/oauth/callback/"

CHALLENGE = 'Bearer realm="OAuth", resource_metadata="https://srv.example.com/.well-known/oauth-protected-resource/mcp", scope="read write"'
RESOURCE_METADATA = {"resource": "https://srv.example.com/mcp", "authorization_servers": ["https://srv.example.com"]}
AS_METADATA = {
    "authorization_endpoint": "https://srv.example.com/authorize",
    "token_endpoint": "https://srv.example.com/token",
    "registration_endpoint": "https://srv.example.com/register",
}


@pytest.fixture(autouse=True)
def _resolve_stand_in_hosts():
    """Let the made-up hostnames in these tests resolve, without reaching a real resolver.

    Literal addresses and ``localhost`` keep their true meaning, so the checks that depend on an
    address being private still test what they claim to.
    """
    real = socket.getaddrinfo

    def fake(host, *args, **kwargs):
        if host == "localhost":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]
        try:
            ipaddress.ip_address(host)
        except ValueError:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
        return real(host, *args, **kwargs)

    with patch("enthusiast_common.oauth.client.socket.getaddrinfo", side_effect=fake):
        yield


def _response(status_code=200, json_body=None, headers=None):
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.headers = headers or {}
    response.json.return_value = json_body or {}
    response.raise_for_status.return_value = None
    response.is_redirect = False
    return response


def _client_returning(post=None, gets=None):
    """A stand-in httpx client. Requests are served in order: the first reply, then `gets`."""
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.request.side_effect = [post or _response(), *(gets or [])]
    return client


class TestDiscover:
    def test_walks_the_challenge_to_the_authorization_server(self):
        client = _client_returning(
            post=_response(401, headers={"WWW-Authenticate": CHALLENGE}),
            gets=[_response(json_body=RESOURCE_METADATA), _response(json_body=AS_METADATA)],
        )

        with patch("enthusiast_common.oauth.client._client", return_value=client):
            server = discover("https://srv.example.com/mcp")

        assert server.authorization_endpoint == "https://srv.example.com/authorize"
        assert server.token_endpoint == "https://srv.example.com/token"
        assert server.registration_endpoint == "https://srv.example.com/register"
        assert server.scopes == ["read", "write"]
        assert server.resource == "https://srv.example.com/mcp"

    def test_a_server_needing_no_token_is_reported_rather_than_guessed_at(self):
        client = _client_returning(post=_response(200))

        with patch("enthusiast_common.oauth.client._client", return_value=client):
            with pytest.raises(OAuthError, match="did not ask for authorization"):
                discover("https://open.example.com/mcp")

    def test_falls_back_to_the_origin_when_no_resource_metadata_is_published(self):
        client = _client_returning(
            post=_response(401, headers={"WWW-Authenticate": 'Bearer realm="OAuth"'}),
            gets=[_response(json_body=AS_METADATA)],
        )

        with patch("enthusiast_common.oauth.client._client", return_value=client):
            server = discover("https://srv.example.com/mcp")

        assert server.token_endpoint == "https://srv.example.com/token"

    def test_unreadable_metadata_raises_rather_than_returning_a_half_built_server(self):
        client = _client_returning(
            post=_response(401, headers={"WWW-Authenticate": CHALLENGE}),
            gets=[httpx.ConnectError("boom"), httpx.ConnectError("boom"), httpx.ConnectError("boom")],
        )

        with patch("enthusiast_common.oauth.client._client", return_value=client):
            with pytest.raises(OAuthError, match="publishes no OAuth metadata"):
                discover("https://srv.example.com/mcp")


class TestIntegrationOAuthHooks:
    def test_oauth_start_needs_a_url(self):
        with pytest.raises(OAuthError, match="Enter the server URL"):
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

    def test_oauth_exchange_code_fills_the_auth_fields_the_form_already_has(self):
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
            config = MCPServerIntegration.oauth_exchange_code(pending, "code-1")

        assert config == {"auth_header": "Authorization", "auth_token": "Bearer tok"}