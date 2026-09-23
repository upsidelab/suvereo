import asyncio
from unittest.mock import AsyncMock, patch

from enthusiast_integration_mcp.integration import MCPServerIntegration


class TestMCPServerIntegrationInstanceName:
    def _integration(self, url):
        integration = MCPServerIntegration()
        integration.set_runtime_arguments({"configuration_args": {"url": url}})
        return integration

    def test_instance_name_identifies_the_server_by_host(self):
        assert self._integration("https://tools.example.com/mcp").instance_name() == "MCP Server (tools.example.com)"

    def test_two_servers_get_distinguishable_names(self):
        first = self._integration("https://a.example.com/mcp").instance_name()
        second = self._integration("https://b.example.com/mcp").instance_name()

        assert first != second

    def test_instance_name_falls_back_to_the_type_name_without_a_host(self):
        assert self._integration("not-a-url").instance_name() == "MCP Server"


class TestMCPServerIntegrationGetTools:
    """The adapter and client are mocked: these pin the config we hand to fastmcp, not fastmcp itself."""

    def _get_tools(self, config, returned=()):
        integration = MCPServerIntegration()
        integration.set_runtime_arguments({"configuration_args": config})
        with (
            patch("enthusiast_integration_mcp.integration.Client") as mock_client_cls,
            patch("enthusiast_integration_mcp.integration.MCPAdapter") as mock_adapter_cls,
        ):
            mock_adapter_cls.return_value.list_tools = AsyncMock(return_value=list(returned))
            tools = asyncio.run(integration.get_tools())
        return tools, mock_client_cls, mock_adapter_cls

    def test_get_tools_builds_a_client_from_own_config_and_returns_its_tools(self):
        tools, mock_client_cls, mock_adapter_cls = self._get_tools(
            {"url": "https://example.com/mcp", "transport": "http", "auth_token": "Bearer secret"},
            returned=["tool_a", "tool_b"],
        )

        assert tools == ["tool_a", "tool_b"]
        assert mock_client_cls.call_args[0][0] == {
            "mcpServers": {
                "mcp_server": {
                    "url": "https://example.com/mcp",
                    "transport": "http",
                    "headers": {"Authorization": "Bearer secret"},
                }
            }
        }
        # the adapter is handed the configured client, not the raw config
        mock_adapter_cls.assert_called_once_with(mock_client_cls.return_value)

    def test_get_tools_enables_response_caching(self):
        _, mock_client_cls, _ = self._get_tools({"url": "https://example.com/mcp"})

        assert mock_client_cls.call_args[1]["cache"] is True

    def test_get_tools_omits_headers_when_no_token_configured(self):
        _, mock_client_cls, _ = self._get_tools({"url": "https://example.com/mcp", "transport": "sse"})

        server = mock_client_cls.call_args[0][0]["mcpServers"]["mcp_server"]
        assert "headers" not in server
        assert server["transport"] == "sse"

    def test_get_tools_sends_the_token_under_a_custom_header_name(self):
        _, mock_client_cls, _ = self._get_tools(
            {"url": "https://example.com/mcp", "auth_header": "X-API-Key", "auth_token": "raw-key"}
        )

        server = mock_client_cls.call_args[0][0]["mcpServers"]["mcp_server"]
        assert server["headers"] == {"X-API-Key": "raw-key"}
        assert server["transport"] == "http"
