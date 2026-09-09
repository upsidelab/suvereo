from typing import Literal

from enthusiast_common.utils import RequiredFieldsModel
from pydantic import Field


class MCPServerConfigArgs(RequiredFieldsModel):
    """Connection details for one MCP server, supplied by the admin configuring the integration."""

    url: str = Field(title="Server URL", description="Full URL of the MCP endpoint, e.g. https://example.com/mcp")
    transport: Literal["sse", "streamable_http"] = Field(
        title="Transport",
        description="How to talk to the server: 'streamable_http' (recommended) or 'sse'",
        default="streamable_http",
    )
    headers: dict[str, str] = Field(
        title="Headers",
        description='JSON object of headers sent on every request, e.g. {"Authorization": "Bearer <token>"}',
        default_factory=dict,
    )
