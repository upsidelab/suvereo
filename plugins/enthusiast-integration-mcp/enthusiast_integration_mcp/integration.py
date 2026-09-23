from typing import Any
from urllib.parse import urlparse

from enthusiast_common.integrations import BaseToolProvidingIntegration
from fastmcp import Client
from langchain.mcp import MCPAdapter
from langchain_core.tools import BaseTool

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

        The client is scoped to this one server, so an unreachable server cannot take the others
        down with it. Response caching is enabled; it serves a stored tool list while the server's
        own TTL hint says it is fresh, and stays inert against servers that publish no hint.
        """
        config: MCPServerConfigArgs = self.CONFIGURATION_ARGS
        server: dict[str, Any] = {"url": config.url, "transport": config.transport}
        if headers := config.as_headers():
            server["headers"] = headers
        client = Client({"mcpServers": {self.TYPE: server}}, cache=True)
        return await MCPAdapter(client).list_tools()
