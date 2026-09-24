from urllib.parse import urlparse

from enthusiast_common.integrations import BaseToolProvidingIntegration
from fastmcp import Client
from fastmcp.client.transports import ClientTransport, SSETransport, StreamableHttpTransport
from langchain.mcp import MCPAdapter
from langchain_core.tools import BaseTool

from .config import MCPServerConfigArgs

TRANSPORTS: dict[str, type[ClientTransport]] = {
    "http": StreamableHttpTransport,
    "sse": SSETransport,
}


class MCPServerIntegration(BaseToolProvidingIntegration):
    """A single MCP server connected to a dataset. A dataset may hold any number of these."""

    TYPE = "mcp_server"
    NAME = "MCP Server"
    INTEGRATION_TYPE_NAME = "MCP Server"
    CONFIGURATION_ARGS = MCPServerConfigArgs
    ALLOWS_MULTIPLE_INSTANCES = True

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
