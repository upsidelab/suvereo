from typing import Any

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

    async def get_tools(self) -> list[BaseTool]:
        """Connect to this server and return its tools as native LangChain tools.

        Uses a client scoped to just this one server: MultiServerMCPClient.get_tools() aborts
        the whole call if any server sharing that client is unreachable, so each integration
        instance must never share a client with another.
        """
        config: MCPServerConfigArgs = self.CONFIGURATION_ARGS
        connection: dict[str, Any] = {"transport": config.transport, "url": config.url}
        if config.headers:
            connection["headers"] = config.headers
        client = MultiServerMCPClient({self.TYPE: connection})
        return await client.get_tools()
