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
    def test_get_tools_builds_client_from_own_config_and_returns_its_tools(self):
        integration = MCPServerIntegration()
        integration.set_runtime_arguments(
            {
                "configuration_args": {
                    "url": "https://example.com/mcp",
                    "transport": "streamable_http",
                    "auth_token": "Bearer secret",
                }
            }
        )

        with patch("enthusiast_integration_mcp.integration.MultiServerMCPClient") as mock_client_cls:
            mock_client_cls.return_value.get_tools = AsyncMock(return_value=["tool_a", "tool_b"])

            tools = asyncio.run(integration.get_tools())

        assert tools == ["tool_a", "tool_b"]
        mock_client_cls.assert_called_once_with(
            {
                "mcp_server": {
                    "transport": "streamable_http",
                    "url": "https://example.com/mcp",
                    "headers": {"Authorization": "Bearer secret"},
                }
            }
        )

    def test_get_tools_omits_headers_key_when_no_token_configured(self):
        integration = MCPServerIntegration()
        integration.set_runtime_arguments(
            {"configuration_args": {"url": "https://example.com/mcp", "transport": "sse"}}
        )

        with patch("enthusiast_integration_mcp.integration.MultiServerMCPClient") as mock_client_cls:
            mock_client_cls.return_value.get_tools = AsyncMock(return_value=[])

            asyncio.run(integration.get_tools())

        connection = mock_client_cls.call_args[0][0]["mcp_server"]
        assert "headers" not in connection

    def test_get_tools_sends_the_token_under_a_custom_header_name(self):
        integration = MCPServerIntegration()
        integration.set_runtime_arguments(
            {
                "configuration_args": {
                    "url": "https://example.com/mcp",
                    "auth_header": "X-API-Key",
                    "auth_token": "raw-key",
                }
            }
        )

        with patch("enthusiast_integration_mcp.integration.MultiServerMCPClient") as mock_client_cls:
            mock_client_cls.return_value.get_tools = AsyncMock(return_value=[])

            asyncio.run(integration.get_tools())

        connection = mock_client_cls.call_args[0][0]["mcp_server"]
        assert connection["headers"] == {"X-API-Key": "raw-key"}
        assert connection["transport"] == "streamable_http"

