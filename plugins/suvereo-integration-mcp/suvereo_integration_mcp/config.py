import time
from typing import Literal

from pydantic import Field
from suvereo_common.utils import RequiredFieldsModel

HIDDEN = {"hidden": True}

EXPIRY_MARGIN_SECONDS = 60.0

RENEW_BACKOFF_SECONDS = 60

RENEW_ATTEMPTS_BEFORE_GIVING_UP = 10


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
    refresh_token: str = Field(default="", json_schema_extra=HIDDEN)
    token_endpoint: str = Field(default="", json_schema_extra=HIDDEN)
    client_id: str = Field(default="", json_schema_extra=HIDDEN)
    expires_at: float = Field(default=0.0, json_schema_extra=HIDDEN)
    renew_failures: int = Field(default=0, json_schema_extra=HIDDEN)
    renew_failed_at: float = Field(default=0.0, json_schema_extra=HIDDEN)

    def can_refresh(self) -> bool:
        """Whether enough was kept from the handshake to ask for a new token."""
        return bool(self.refresh_token and self.token_endpoint and self.client_id)

    def should_renew(self) -> bool:
        """Whether this token has lapsed and there is something to replace it with."""
        if not self.expires_at or not self.can_refresh() or self.needs_reconnect():
            return False
        if time.time() - self.renew_failed_at < RENEW_BACKOFF_SECONDS:
            return False
        return time.time() + EXPIRY_MARGIN_SECONDS >= self.expires_at

    def needs_reconnect(self) -> bool:
        """Whether renewal has failed often enough that only a fresh authorization will fix it."""
        return self.renew_failures >= RENEW_ATTEMPTS_BEFORE_GIVING_UP

    def as_headers(self) -> dict[str, str]:
        """The headers to send on every request to this server.

        Credentials are stored as two scalar fields rather than a header mapping so that the admin
        form, which renders one text input per field, can express them. That covers the bearer and
        API-key schemes real servers use; anything more exotic needs a richer form first.
        """
        if not self.auth_token:
            return {}
        return {self.auth_header: self.auth_token}
