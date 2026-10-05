import ipaddress
import socket
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from enthusiast_common.oauth import (
    AuthorizationServer,
    OAuthError,
    build_authorization_url,
    discover_from_challenge,
    exchange_code,
    register_client,
    require_public_url,
)

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

    with patch("enthusiast_common.oauth.http.socket.getaddrinfo", side_effect=fake):
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


class TestRedirectsAreFollowedOneHopAtATime:
    """Providers do redirect, but a hop must not be able to land the server on its own network."""

    def _redirect(self, to):
        response = _response(302, headers={"Location": to})
        response.is_redirect = True
        response.next_request = None
        return response

    def test_a_hop_to_a_private_address_is_refused(self):
        client = _client_returning()
        client.request.side_effect = None
        client.request.return_value = self._redirect("http://169.254.169.254/latest/meta-data/")

        with patch("enthusiast_common.oauth.http.open_client", return_value=client):
            with pytest.raises(OAuthError, match="private address"):
                discover_from_challenge("https://srv.example.com/mcp", CHALLENGE)

    def test_a_public_hop_is_followed(self):
        client = _client_returning()
        client.request.side_effect = [
            self._redirect("https://canonical.example.com/mcp"),
            _response(401, headers={"WWW-Authenticate": 'Bearer realm="OAuth"'}),
            _response(json_body=AS_METADATA),
        ]
        with patch("enthusiast_common.oauth.http.open_client", return_value=client):
            server = discover_from_challenge("https://srv.example.com/mcp", CHALLENGE)

        assert server.token_endpoint == "https://srv.example.com/token"

    def test_a_redirect_loop_gives_up(self):
        client = _client_returning()
        client.request.side_effect = None
        client.request.return_value = self._redirect("https://srv.example.com/mcp")

        with patch("enthusiast_common.oauth.http.open_client", return_value=client):
            with pytest.raises(OAuthError, match="redirected too many times"):
                discover_from_challenge("https://srv.example.com/mcp", CHALLENGE)


class TestRequirePublicUrl:
    """Everything here is fetched by the server, so a form value must not reach its own network."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:8931/mcp",
            "http://localhost/mcp",
            "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.5/mcp",
            "http://192.168.1.10/mcp",
        ],
    )
    def test_addresses_on_our_own_network_are_refused(self, url):
        with pytest.raises(OAuthError, match="private address"):
            require_public_url(url)

    @pytest.mark.parametrize("url", ["file:///etc/passwd", "gopher://example.com", "ftp://example.com"])
    def test_only_http_is_fetched(self, url):
        with pytest.raises(OAuthError, match="http:// or https:// URL"):
            require_public_url(url)

    def test_a_public_url_passes_through_unchanged(self):
        with patch(
            "enthusiast_common.oauth.http.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 0))]
        ):
            assert require_public_url("https://example.com/mcp") == "https://example.com/mcp"

    def test_a_name_that_does_not_resolve_is_reported(self):
        with patch("enthusiast_common.oauth.http.socket.getaddrinfo", side_effect=socket.gaierror):
            with pytest.raises(OAuthError, match="Could not resolve"):
                require_public_url("https://nope.invalid/mcp")


class TestRegisterClient:
    def test_registers_as_a_public_client_for_the_callback(self):
        client = _client_returning(post=_response(201, {"client_id": "abc123"}))
        server = AuthorizationServer("https://a/authorize", "https://a/token", "https://a/register", ["read"])

        with patch("enthusiast_common.oauth.http.open_client", return_value=client):
            credentials = register_client(server, REDIRECT, "Enthusiast")

        assert credentials.client_id == "abc123"
        payload = client.request.call_args.kwargs["json"]
        assert payload["redirect_uris"] == [REDIRECT]
        assert payload["token_endpoint_auth_method"] == "none"
        assert "refresh_token" in payload["grant_types"]

    def test_a_server_without_registration_points_at_the_manual_field(self):
        """Such a server still takes a token the admin can make themselves, so say that."""
        server = AuthorizationServer("https://a/authorize", "https://a/token", registration_endpoint=None)

        with pytest.raises(OAuthError, match="paste it into Auth token"):
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

        with patch("enthusiast_common.oauth.http.open_client", return_value=client):
            tokens = exchange_code("https://a/token", "code-1", "verifier-1", "abc123", REDIRECT)

        assert tokens.access_token == "tok"
        sent = client.request.call_args.kwargs["data"]
        assert sent["code_verifier"] == "verifier-1"
        assert sent["grant_type"] == "authorization_code"
        assert sent["redirect_uri"] == REDIRECT

    def test_a_refused_exchange_raises(self):
        client = _client_returning(post=_response(400, {"error": "invalid_grant"}))

        with patch("enthusiast_common.oauth.http.open_client", return_value=client):
            with pytest.raises(OAuthError, match="refused the token exchange"):
                exchange_code("https://a/token", "code-1", "verifier-1", "abc123", REDIRECT)
