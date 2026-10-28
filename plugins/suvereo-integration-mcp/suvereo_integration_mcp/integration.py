import asyncio
import logging
import time
from typing import Any
from urllib.parse import urlparse

import httpx
from suvereo_common.integrations import BaseOAuthIntegration, BaseToolProvidingIntegration
from suvereo_common.oauth import (
    OAuthAuthorizationRequest,
    OAuthClientCredentials,
    OAuthError,
    OAuthPendingAuthorization,
    OAuthTokens,
    build_authorization_url,
    exchange_code,
    refresh_tokens,
    register_client,
)
from fastmcp import Client
from fastmcp.client.transports import ClientTransport, SSETransport, StreamableHttpTransport
from langchain.mcp import MCPAdapter
from langchain_core.tools import BaseTool

from .config import MCPServerConfigArgs
from .oauth import discover

TRANSPORTS: dict[str, type[ClientTransport]] = {
    "http": StreamableHttpTransport,
    "sse": SSETransport,
}

OAUTH_CLIENT_NAME = "Suvereo"

# What a token carries when it cannot be renewed.
NOTHING_TO_RENEW_WITH = {
    "refresh_token": "",
    "token_endpoint": "",
    "client_id": "",
    "expires_at": 0.0,
    "renew_failures": 0,
    "renew_failed_at": 0.0,
}

logger = logging.getLogger(__name__)


class MCPServerIntegration(BaseToolProvidingIntegration, BaseOAuthIntegration):
    """A single MCP server connected to a dataset. A dataset may hold any number of these."""

    TYPE = "mcp_server"
    NAME = "MCP Server"
    INTEGRATION_TYPE_NAME = "MCP Server"
    CONFIGURATION_ARGS = MCPServerConfigArgs
    ALLOWS_MULTIPLE_INSTANCES = True
    OAUTH_FIELD = "url"
    OAUTH_REFRESH_FIELD = "refresh_token"

    @classmethod
    def oauth_start(
        cls, target: str, redirect_uri: str, client: OAuthClientCredentials | None = None
    ) -> OAuthAuthorizationRequest:
        """Discover the server's authorization server and build the URL to send the admin to.

        Args:
            target: The server URL.
            redirect_uri: Where the authorization server must send the admin back to.
            client: Credentials from a previous registration against this server, reused when
                given so that pressing Connect again does not register another client.

        Returns:
            The authorization URL, and the state the callback needs to finish the exchange. The
            state carries ``client`` back out, for the caller to keep and pass in next time.

        Raises:
            OAuthError: If the server needs no token, or cannot be registered with.
        """
        url = target.strip()
        if not url:
            raise OAuthError("Enter the server URL before connecting.")

        server = discover(url)
        credentials = client or register_client(server, redirect_uri, client_name=OAUTH_CLIENT_NAME)
        authorization_url, verifier, state = build_authorization_url(server, credentials.client_id, redirect_uri)
        pending = OAuthPendingAuthorization(
            state=state,
            verifier=verifier,
            client=credentials,
            token_endpoint=server.token_endpoint,
            redirect_uri=redirect_uri,
            resource=server.resource,
            renewable=server.issues_refresh_tokens(),
        )
        return OAuthAuthorizationRequest(authorization_url=authorization_url, pending=pending)

    @classmethod
    def oauth_exchange_code(cls, pending: OAuthPendingAuthorization, code: str) -> dict[str, Any]:
        """Exchange the authorization code for a token, as fields to merge into the config.

        Args:
            pending: The state returned by ``oauth_start``.
            code: The authorization code the callback received.

        Returns:
            The token to use, together with what is needed to renew it later.
        """
        tokens = exchange_code(
            token_endpoint=pending.token_endpoint,
            code=code,
            verifier=pending.verifier,
            client_id=pending.client.client_id,
            redirect_uri=pending.redirect_uri,
            client_secret=pending.client.client_secret,
            resource=pending.resource,
        )
        return cls._config_from_tokens(
            tokens,
            pending.token_endpoint,
            pending.client.client_id,
            renewable=pending.renewable,
        )

    @classmethod
    def oauth_refresh(cls, config: dict[str, Any]) -> dict[str, Any]:
        """Renew the stored token, as fields to merge into the config."""
        stored = MCPServerConfigArgs(**config)
        if not stored.can_refresh():
            raise OAuthError("This server was not connected with Connect, so there is nothing to renew.")

        tokens = refresh_tokens(stored.token_endpoint, stored.refresh_token, stored.client_id)
        return cls._config_from_tokens(
            tokens,
            stored.token_endpoint,
            stored.client_id,
            fallback_refresh_token=stored.refresh_token,
        )

    @staticmethod
    def _config_from_tokens(
        tokens: OAuthTokens,
        token_endpoint: str,
        client_id: str,
        fallback_refresh_token: str = "",
        renewable: bool = True,
    ) -> dict[str, Any]:
        """Turn a token response into stored config."""
        token_type = tokens.token_type or "Bearer"
        expires_in = tokens.expires_in
        renewal = (
            {
                "refresh_token": tokens.refresh_token or fallback_refresh_token,
                "token_endpoint": token_endpoint,
                "client_id": client_id,
                "expires_at": (time.time() + float(expires_in)) if expires_in else 0.0,
            }
            if renewable
            else {}
        )
        return {
            **NOTHING_TO_RENEW_WITH,
            "auth_header": "Authorization",
            "auth_token": f"{token_type.title()} {tokens.access_token}",
            **renewal,
        }

    def instance_name(self) -> str:
        """The admin-supplied name, falling back to the host for servers configured without one."""
        if name := self.CONFIGURATION_ARGS.name.strip():
            return name
        host = urlparse(self.CONFIGURATION_ARGS.url).netloc
        return f"{self.NAME} ({host})" if host else self.NAME

    def needs_reconnect(self) -> bool:
        """Whether this server has stopped renewing and has to be connected again by hand."""
        return self.CONFIGURATION_ARGS.needs_reconnect()

    async def _renew_if_needed(self) -> None:
        """Replace the stored token when it has lapsed, keeping the new one."""
        config: MCPServerConfigArgs = self.CONFIGURATION_ARGS
        if not config.should_renew():
            return
        try:
            patch = await asyncio.to_thread(self.oauth_refresh, config.model_dump())
        except (OAuthError, httpx.HTTPError):
            logger.warning("Could not renew the token for %s", self.instance_name(), exc_info=True)
            patch = {"renew_failures": config.renew_failures + 1, "renew_failed_at": time.time()}

        await self._apply(patch)

    async def _apply(self, patch: dict[str, Any]) -> None:
        """Keep a change to this instance's configuration, in memory and wherever it is stored."""
        current = self.CONFIGURATION_ARGS.model_dump()
        self.CONFIGURATION_ARGS = MCPServerConfigArgs(**{**current, **patch})
        if self._config_writer:
            await self._config_writer(patch)

    async def get_tools(self) -> list[BaseTool]:
        """Connect to this server and return its tools as native LangChain tools.

        The client is scoped to this one server, so an unreachable server cannot take the others
        down with it. Response caching is enabled; it serves a stored tool list while the server's
        own TTL hint says it is fresh, and stays inert against servers that publish no hint.
        """
        await self._renew_if_needed()
        config: MCPServerConfigArgs = self.CONFIGURATION_ARGS
        transport = TRANSPORTS[config.transport](url=config.url, headers=config.as_headers() or None)
        return await MCPAdapter(Client(transport, cache=True)).list_tools()
