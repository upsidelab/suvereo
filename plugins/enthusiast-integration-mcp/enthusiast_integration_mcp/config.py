from typing import Literal

from enthusiast_common.utils import RequiredFieldsModel
from pydantic import Field


class MCPServerConfigArgs(RequiredFieldsModel):
    """Connection details for one MCP server, supplied by the admin configuring the integration."""

    url: str = Field(title="Server URL", description="Full URL of the MCP endpoint, e.g. https://example.com/mcp")
    transport: Literal["http", "sse"] = Field(
        title="Transport",
        description="How to talk to the server: 'http' (recommended) or 'sse' for older servers",
        default="http",
    )
    auth_header: str = Field(
        title="Auth header",
        description="Name of the header the credential is sent in. Ignored when no token is given.",
        default="Authorization",
    )
    auth_token: str = Field(
        title="Auth token",
        description=(
            "Full value of the auth header, including any scheme - for example 'Bearer abc123'. "
            "Leave empty for a server that needs no authentication."
        ),
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
