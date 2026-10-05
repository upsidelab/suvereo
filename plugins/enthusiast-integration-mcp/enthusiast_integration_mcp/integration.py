from urllib.parse import urlparse

from enthusiast_common.integrations import BaseOAuthIntegration, BaseToolProvidingIntegration
from enthusiast_common.oauth import (
    OAuthAuthorizationRequest,
    OAuthClientCredentials,
    OAuthError,
    OAuthPendingAuthorization,
    build_authorization_url,
    exchange_code,
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

OAUTH_CLIENT_NAME = "Enthusiast"


class MCPServerIntegration(BaseToolProvidingIntegration, BaseOAuthIntegration):
    """A single MCP server connected to a dataset. A dataset may hold any number of these."""

    TYPE = "mcp_server"
    NAME = "MCP Server"
    INTEGRATION_TYPE_NAME = "MCP Server"
    CONFIGURATION_ARGS = MCPServerConfigArgs
    ALLOWS_MULTIPLE_INSTANCES = True
    OAUTH_FIELD = "url"

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
        )
        return OAuthAuthorizationRequest(authorization_url=authorization_url, pending=pending)

    @classmethod
    def oauth_exchange_code(cls, pending: OAuthPendingAuthorization, code: str) -> dict[str, str]:
        """Exchange the authorization code for a token, as fields to merge into the config.

        Args:
            pending: The state returned by ``oauth_start``.
            code: The authorization code the callback received.

        Returns:
            The ``auth_header``/``auth_token`` pair, ready to drop into the form.
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
        token_type = tokens.token_type or "Bearer"
        return {
            "auth_header": "Authorization",
            "auth_token": f"{token_type.title()} {tokens.access_token}",
        }

    def instance_name(self) -> str:
        """The admin-supplied name, falling back to the host for servers configured without one."""
        if name := self.CONFIGURATION_ARGS.name.strip():
            return name
        host = urlparse(self.CONFIGURATION_ARGS.url).netloc
        return f"{self.NAME} ({host})" if host else self.NAME

    async def get_tools(self) -> list[BaseTool]:
        """Connect to this server and return its tools as native LangChain tools.

        The client is scoped to this one server, so an unreachable server cannot take the others
        down with it. Response caching is enabled; it serves a stored tool list while the server's
        own TTL hint says it is fresh, and stays inert against servers that publish no hint.
        """
        config: MCPServerConfigArgs = self.CONFIGURATION_ARGS
        transport = TRANSPORTS[config.transport](url=config.url, headers=config.as_headers() or None)
        return await MCPAdapter(Client(transport, cache=True)).list_tools()
