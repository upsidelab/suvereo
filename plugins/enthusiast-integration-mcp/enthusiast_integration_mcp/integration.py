from typing import Any
from urllib.parse import urlparse

from enthusiast_common.integrations import BaseToolProvidingIntegration
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from .config import MCPServerConfigArgs


class MCPServerIntegration(BaseToolProvidingIntegration):
    """A single MCP server connected to a dataset. A dataset may hold any number of these."""

    TYPE = "mcp_server"
    NAME = "MCP Server"
    INTEGRATION_TYPE_NAME = "MCP Server"
    CONFIGURATION_ARGS = MCPServerConfigArgs
    ALLOWS_MULTIPLE_INSTANCES = True

    def instance_name(self) -> str:
        """Name this server by its host, so several connected servers are told apart in the UI."""
        host = urlparse(self.CONFIGURATION_ARGS.url).netloc
        return f"{self.NAME} ({host})" if host else self.NAME

    async def get_tools(self) -> list[BaseTool]:
        """Connect to this server and return its tools as native LangChain tools.

        Uses a client scoped to just this one server: MultiServerMCPClient.get_tools() aborts
        the whole call if any server sharing that client is unreachable, so each integration
        instance must never share a client with another.
        """
        config: MCPServerConfigArgs = self.CONFIGURATION_ARGS
        connection: dict[str, Any] = {"transport": config.transport, "url": config.url}
        if headers := config.as_headers():
            connection["headers"] = headers
        client = MultiServerMCPClient({self.TYPE: connection})
        return await client.get_tools()
