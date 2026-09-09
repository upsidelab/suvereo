import asyncio
from unittest.mock import AsyncMock, patch

from enthusiast_integration_mcp.integration import MCPServerIntegration


class TestMCPServerIntegrationGetTools:
    def test_get_tools_builds_client_from_own_config_and_returns_its_tools(self):
        integration = MCPServerIntegration()
        integration.set_runtime_arguments(
            {
                "configuration_args": {
                    "url": "https://example.com/mcp",
                    "transport": "streamable_http",
                    "headers": {"Authorization": "Bearer secret"},
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

    def test_get_tools_omits_headers_key_when_none_configured(self):
        integration = MCPServerIntegration()
        integration.set_runtime_arguments(
            {"configuration_args": {"url": "https://example.com/mcp", "transport": "sse"}}
        )

        with patch("enthusiast_integration_mcp.integration.MultiServerMCPClient") as mock_client_cls:
            mock_client_cls.return_value.get_tools = AsyncMock(return_value=[])

            asyncio.run(integration.get_tools())

        connection = mock_client_cls.call_args[0][0]["mcp_server"]
        assert "headers" not in connection

