from typing import Literal

from enthusiast_common.utils import RequiredFieldsModel
from pydantic import Field


class MCPServerConfigArgs(RequiredFieldsModel):
    """Connection details for one MCP server, supplied by the admin configuring the integration."""

    url: str
    transport: Literal["sse", "streamable_http"]
    headers: dict[str, str] = Field(default_factory=dict)
