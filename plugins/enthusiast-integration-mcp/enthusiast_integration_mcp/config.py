from typing import Literal

from enthusiast_common.utils import RequiredFieldsModel
from pydantic import Field


class MCPServerConfigArgs(RequiredFieldsModel):
    """Connection details for one MCP server, supplied by the admin configuring the integration."""

    name: str = Field(
        title="Name",
        description="Defaults to the server's host.",
        default="",
    )
    url: str = Field(title="Server URL", description="For example https://example.com/mcp")
    transport: Literal["http", "sse"] = Field(
        title="Transport",
        description="Use sse only for older servers.",
        default="http",
    )
    auth_header: str = Field(
        title="Auth header",
        description="Ignored when no token is given.",
        default="Authorization",
    )
    auth_token: str = Field(
        title="Auth token",
        description="Include the scheme, e.g. 'Bearer abc123'. Leave empty if none is needed.",
        default="",
    )

    def as_headers(self) -> dict[str, str]:
        """The headers to send on every request to this server.

        Credentials are stored as two scalar fields rather than a header mapping so that the admin
        form, which renders one text input per field, can express them. That covers the bearer and
        API-key schemes real servers use; anything more exotic needs a richer form first.
        """
        if not self.auth_token:
            return {}
        return {self.auth_header: self.auth_token}
