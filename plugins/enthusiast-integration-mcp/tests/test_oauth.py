import asyncio
import ipaddress
import socket
import time
from unittest.mock import MagicMock, patch

import httpx
import pytest
from enthusiast_common.oauth import (
    AuthorizationServer,
    NoAuthorizationRequired,
    OAuthClientCredentials,
    OAuthError,
    OAuthPendingAuthorization,
    OAuthTokens,
)
from enthusiast_integration_mcp.config import MCPServerConfigArgs
from enthusiast_integration_mcp.integration import MCPServerIntegration
from enthusiast_integration_mcp.oauth import discover

REDIRECT = "https://enthusiast.example.com/api/integrations/oauth/callback/"


def _pending(**overrides) -> OAuthPendingAuthorization:
    """A pending authorization against https://a/token for client ``abc``, with any field overridden."""
    fields = {
        "state": "s",
        "verifier": "v",
        "client": OAuthClientCredentials(client_id="abc"),
        "token_endpoint": "https://a/token",
        "redirect_uri": REDIRECT,
    }
    return OAuthPendingAuthorization(**{**fields, **overrides})


CHALLENGE = (
    'Bearer realm="OAuth", '
    'resource_metadata="https://srv.example.com/.well-known/oauth-protected-resource/mcp", '
    'scope="read write"'
)
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


class TestDiscover:
    def test_walks_the_challenge_to_the_authorization_server(self):
        client = _client_returning(
            post=_response(401, headers={"WWW-Authenticate": CHALLENGE}),
            gets=[_response(json_body=RESOURCE_METADATA), _response(json_body=AS_METADATA)],
        )

        with patch("enthusiast_common.oauth.http.open_client", return_value=client):
            server = discover("https://srv.example.com/mcp")

        assert server.authorization_endpoint == "https://srv.example.com/authorize"
        assert server.token_endpoint == "https://srv.example.com/token"
        assert server.registration_endpoint == "https://srv.example.com/register"
        assert server.scopes == ["read", "write"]
        assert server.resource == "https://srv.example.com/mcp"

    def test_a_server_needing_no_token_is_reported_as_such_not_as_a_failure(self):
        """The host tells this apart by the flag, so it can say "nothing to do" rather than "error"."""
        client = _client_returning(post=_response(200))

        with patch("enthusiast_common.oauth.http.open_client", return_value=client):
            with pytest.raises(NoAuthorizationRequired, match="needs no token"):
                discover("https://open.example.com/mcp")

    def test_falls_back_to_the_origin_when_no_resource_metadata_is_published(self):
        client = _client_returning(
            post=_response(401, headers={"WWW-Authenticate": 'Bearer realm="OAuth"'}),
            gets=[_response(json_body=AS_METADATA)],
        )

        with patch("enthusiast_common.oauth.http.open_client", return_value=client):
            server = discover("https://srv.example.com/mcp")

        assert server.token_endpoint == "https://srv.example.com/token"

    def test_unreadable_metadata_raises_rather_than_returning_a_half_built_server(self):
        client = _client_returning(
            post=_response(401, headers={"WWW-Authenticate": CHALLENGE}),
            gets=[httpx.ConnectError("boom"), httpx.ConnectError("boom"), httpx.ConnectError("boom")],
        )

        with patch("enthusiast_common.oauth.http.open_client", return_value=client):
            with pytest.raises(OAuthError, match="publishes no OAuth metadata"):
                discover("https://srv.example.com/mcp")


class TestIntegrationOAuthHooks:
    def test_oauth_start_needs_a_url(self):
        with pytest.raises(OAuthError, match="Enter the server URL"):
            MCPServerIntegration.oauth_start("  ", REDIRECT)

    def test_oauth_start_returns_the_state_the_callback_needs(self):
        server = AuthorizationServer("https://a/authorize", "https://a/token", "https://a/register")

        with (
            patch("enthusiast_integration_mcp.integration.discover", return_value=server),
            patch(
                "enthusiast_integration_mcp.integration.register_client",
                return_value=OAuthClientCredentials(client_id="abc"),
            ),
        ):
            authorization = MCPServerIntegration.oauth_start("https://srv/mcp", REDIRECT)

        pending = authorization.pending
        assert authorization.authorization_url.startswith("https://a/authorize")
        assert pending.client.client_id == "abc"
        assert pending.token_endpoint == "https://a/token"
        assert pending.redirect_uri == REDIRECT
        assert pending.verifier and pending.state

    def test_oauth_exchange_code_fills_the_auth_fields_the_form_already_has(self):
        pending = OAuthPendingAuthorization(
            state="s",
            verifier="v",
            client=OAuthClientCredentials(client_id="abc"),
            token_endpoint="https://a/token",
            redirect_uri=REDIRECT,
        )

        with patch(
            "enthusiast_integration_mcp.integration.exchange_code",
            return_value=OAuthTokens(access_token="tok", token_type="bearer"),
        ):
            config = MCPServerIntegration.oauth_exchange_code(pending, "code-1")

        assert config["auth_header"] == "Authorization"
        assert config["auth_token"] == "Bearer tok"

    def test_oauth_exchange_code_keeps_what_is_needed_to_renew(self):
        pending = _pending()

        with patch(
            "enthusiast_integration_mcp.integration.exchange_code",
            return_value=OAuthTokens(access_token="tok", refresh_token="r1", expires_in=3600),
        ):
            config = MCPServerIntegration.oauth_exchange_code(pending, "code-1")

        assert config["refresh_token"] == "r1"
        assert config["token_endpoint"] == "https://a/token"
        assert config["client_id"] == "abc"
        assert config["expires_at"] > time.time()

    def test_a_token_with_no_stated_lifetime_is_never_treated_as_expiring(self):
        """Some servers issue tokens that do not expire; renewing those would be pointless."""
        with patch(
            "enthusiast_integration_mcp.integration.exchange_code",
            return_value=OAuthTokens(access_token="tok"),
        ):
            config = MCPServerIntegration.oauth_exchange_code(_pending(), "code-1")

        assert config["expires_at"] == 0.0
        assert MCPServerConfigArgs(url="https://srv/mcp", expires_at=0.0).should_renew() is False


class TestRenewal:
    """A token renewed only in memory is lost the moment the request ends."""

    def _integration(self, **overrides):
        config = {
            "url": "https://srv.example.com/mcp",
            "auth_token": "Bearer old",
            "refresh_token": "r1",
            "token_endpoint": "https://srv.example.com/token",
            "client_id": "abc",
            "expires_at": time.time() - 1,
            **overrides,
        }
        integration = MCPServerIntegration()
        integration.set_runtime_arguments({"configuration_args": config})
        return integration

    def _renew(self, integration, tokens=None, error=None):
        written = []

        async def writer(patch):
            written.append(patch)

        integration.set_config_writer(writer)
        target = "enthusiast_integration_mcp.integration.refresh_tokens"
        with patch(target, side_effect=error) if error else patch(target, return_value=tokens):
            asyncio.run(integration._renew_if_needed())
        return written

    def test_an_expired_token_is_replaced(self):
        integration = self._integration()

        self._renew(integration, tokens=OAuthTokens(access_token="new", expires_in=3600))

        assert integration.CONFIGURATION_ARGS.auth_token == "Bearer new"

    def test_the_new_token_is_handed_back_to_be_stored(self):
        integration = self._integration()

        written = self._renew(integration, tokens=OAuthTokens(access_token="new", expires_in=3600))

        assert written[0]["auth_token"] == "Bearer new"
        assert written[0]["expires_at"] > time.time()

    def test_a_provider_that_issues_no_new_refresh_token_keeps_the_old_one(self):
        integration = self._integration()

        written = self._renew(integration, tokens=OAuthTokens(access_token="new", expires_in=3600))

        assert written[0]["refresh_token"] == "r1"

    def test_a_token_still_valid_is_left_alone(self):
        integration = self._integration(expires_at=time.time() + 3600)

        written = self._renew(integration, tokens=OAuthTokens(access_token="new"))

        assert written == []
        assert integration.CONFIGURATION_ARGS.auth_token == "Bearer old"

    def test_a_hand_configured_token_is_never_renewed(self):
        """Nothing was kept to renew with, and the pasted token may well still work."""
        integration = self._integration(refresh_token="", token_endpoint="", client_id="")

        written = self._renew(integration, tokens=OAuthTokens(access_token="new"))

        assert written == []

    def test_a_refusal_leaves_the_stored_token_in_place(self):
        """The old token may still work, and failing here should read as the server being down."""
        integration = self._integration()

        written = self._renew(integration, error=OAuthError("revoked"))

        assert integration.CONFIGURATION_ARGS.auth_token == "Bearer old"
        assert "auth_token" not in written[0]
        assert written[0]["renew_failures"] == 1


class TestRefreshMaterialIsOnlyKeptWhenUsable:
    def _finish(self, renewable):
        pending = _pending(renewable=renewable)
        with patch(
            "enthusiast_integration_mcp.integration.exchange_code",
            return_value=OAuthTokens(access_token="tok", refresh_token="r1", expires_in=3600),
        ):
            return MCPServerIntegration.oauth_exchange_code(pending, "code-1")

    def test_a_renewing_server_has_its_material_kept(self):
        config = self._finish(renewable=True)

        assert config["refresh_token"] == "r1"
        assert config["expires_at"] > time.time()

    def test_a_server_that_does_not_renew_keeps_only_the_token(self):
        """A Refresh button that can only fail is worse than none, and it must not renew silently."""
        config = self._finish(renewable=False)

        assert config["auth_token"] == "Bearer tok"
        assert config["refresh_token"] == ""
        assert config["token_endpoint"] == ""
        assert config["expires_at"] == 0.0


class TestRenewalBacksOffAfterRepeatedFailure:
    """Renewal runs on every tool fetch, so a revoked grant must not be retried forever."""

    def _integration(self, **overrides):
        config = {
            "url": "https://srv.example.com/mcp",
            "auth_token": "Bearer old",
            "refresh_token": "r1",
            "token_endpoint": "https://srv.example.com/token",
            "client_id": "abc",
            "expires_at": time.time() - 1,
            **overrides,
        }
        integration = MCPServerIntegration()
        integration.set_runtime_arguments({"configuration_args": config})
        return integration

    def _fail_once(self, integration):
        with patch(
            "enthusiast_integration_mcp.integration.refresh_tokens",
            side_effect=OAuthError("revoked"),
        ):
            asyncio.run(integration._renew_if_needed())

    def test_a_failure_is_not_retried_immediately(self):
        integration = self._integration()

        self._fail_once(integration)

        assert integration.CONFIGURATION_ARGS.renew_failures == 1
        assert integration.CONFIGURATION_ARGS.should_renew() is False

    def test_a_blip_is_tried_again_once_the_wait_is_over(self):
        """One failure is more often a hiccup than a revocation, so it keeps trying."""
        integration = self._integration(renew_failures=1, renew_failed_at=time.time() - 61)

        assert integration.CONFIGURATION_ARGS.should_renew() is True

    def test_a_backed_off_token_makes_no_further_calls(self):
        integration = self._integration(renew_failures=1, renew_failed_at=time.time())

        with patch("enthusiast_integration_mcp.integration.refresh_tokens") as called:
            asyncio.run(integration._renew_if_needed())

        called.assert_not_called()

    def test_success_clears_the_record_of_failure(self):
        integration = self._integration(renew_failures=2, renew_failed_at=time.time() - 61)

        with patch(
            "enthusiast_integration_mcp.integration.refresh_tokens",
            return_value=OAuthTokens(access_token="new", expires_in=3600),
        ):
            asyncio.run(integration._renew_if_needed())

        assert integration.CONFIGURATION_ARGS.renew_failures == 0
        assert integration.CONFIGURATION_ARGS.renew_failed_at == 0.0


class TestGivingUpOnRenewal:
    """Backing off for ever is not a resting state: at some point a person has to reconnect it."""

    def _config(self, **overrides):
        return MCPServerConfigArgs(
            url="https://srv.example.com/mcp",
            refresh_token="r1",
            token_endpoint="https://srv.example.com/token",
            client_id="abc",
            expires_at=time.time() - 1,
            **overrides,
        )

    def test_a_few_failures_are_not_enough_to_give_up(self):
        assert self._config(renew_failures=3, renew_failed_at=0).needs_reconnect() is False

    def test_enough_failures_stop_renewal_for_good(self):
        config = self._config(renew_failures=10, renew_failed_at=0)

        assert config.needs_reconnect() is True
        assert config.should_renew() is False

    def test_a_working_server_is_never_flagged(self):
        assert self._config().needs_reconnect() is False

    def test_connecting_again_clears_it(self):
        """oauth_exchange_code resets the counters, so a fresh authorization puts it back in service."""
        with patch(
            "enthusiast_integration_mcp.integration.exchange_code",
            return_value=OAuthTokens(access_token="tok", refresh_token="r2", expires_in=3600),
        ):
            renewed = MCPServerIntegration.oauth_exchange_code(_pending(), "code-1")

        assert renewed["renew_failures"] == 0
        assert MCPServerConfigArgs(url="https://srv/mcp", **renewed).needs_reconnect() is False

    def test_the_integration_reports_it_for_the_host_to_show(self):
        integration = MCPServerIntegration()
        integration.set_runtime_arguments({"configuration_args": self._config(renew_failures=10).model_dump()})

        assert integration.needs_reconnect() is True


class TestANetworkFailureDuringRenewal:
    """A blip must cost the renewal, not the server's tools: the old token is very likely fine."""

    def _integration(self):
        integration = MCPServerIntegration()
        integration.set_runtime_arguments(
            {
                "configuration_args": {
                    "url": "https://srv.example.com/mcp",
                    "auth_token": "Bearer old",
                    "refresh_token": "r1",
                    "token_endpoint": "https://srv.example.com/token",
                    "client_id": "abc",
                    "expires_at": time.time() - 1,
                }
            }
        )
        return integration

    @pytest.mark.parametrize("failure", [httpx.ConnectError("down"), httpx.ReadTimeout("slow")])
    def test_a_transport_error_does_not_escape(self, failure):
        integration = self._integration()

        with patch("enthusiast_integration_mcp.integration.refresh_tokens", side_effect=failure):
            asyncio.run(integration._renew_if_needed())

        assert integration.CONFIGURATION_ARGS.auth_token == "Bearer old"
        assert integration.CONFIGURATION_ARGS.renew_failures == 1

    def test_the_refresh_call_cannot_outlive_the_tool_fetch_budget(self):
        """Its own timeout must stay inside the caller's, or a renewal is abandoned mid-flight."""
        from enthusiast_common.builder.default import DYNAMIC_TOOL_FETCH_TIMEOUT_SECONDS
        from enthusiast_common.oauth import http

        assert http.TIMEOUT < DYNAMIC_TOOL_FETCH_TIMEOUT_SECONDS
