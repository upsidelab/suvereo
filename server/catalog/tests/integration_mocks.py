from enthusiast_common.integrations import BaseIntegration, BaseOAuthIntegration
from enthusiast_common.oauth import OAuthAuthorizationRequest, OAuthClientCredentials, OAuthPendingAuthorization
from enthusiast_common.utils import RequiredFieldsModel
from pydantic import Field


class MockConfigArgs(RequiredFieldsModel):
    marker: str = Field(default="")


class MockSingleInstanceIntegration(BaseIntegration):
    TYPE = "mock_single"
    NAME = "Mock Single Instance"
    INTEGRATION_TYPE_NAME = "Mock category"
    ALLOWS_MULTIPLE_INSTANCES = False


class MockMultiInstanceIntegration(BaseIntegration):
    TYPE = "mock_multi"
    NAME = "Mock Multi Instance"
    INTEGRATION_TYPE_NAME = "Mock category"
    ALLOWS_MULTIPLE_INSTANCES = True
    CONFIGURATION_ARGS = MockConfigArgs

    def instance_name(self) -> str:
        """Label by config, the way a real multi-instance plugin distinguishes its instances."""
        return f"{self.NAME} ({self.CONFIGURATION_ARGS.marker})"


class MockOAuthIntegration(BaseOAuthIntegration):
    """Stands in for a plugin that opts into the OAuth handshake, without talking to a provider."""

    TYPE = "mock_oauth"
    NAME = "Mock OAuth"
    INTEGRATION_TYPE_NAME = "Mock category"

    OAUTH_FIELD = "url"

    @classmethod
    def oauth_start(cls, target, redirect_uri, client=None):
        return OAuthAuthorizationRequest(
            authorization_url="https://provider.example.com/authorize?state=state-123",
            pending=mock_pending_authorization(
                redirect_uri=redirect_uri, client=client or OAuthClientCredentials(client_id="registered-once")
            ),
        )

    @classmethod
    def oauth_refresh(cls, config):
        return {"auth_token": "Bearer renewed"}

    @classmethod
    def oauth_exchange_code(cls, pending, code):
        return {"auth_header": "Authorization", "auth_token": f"Bearer token-for-{code}"}


def mock_pending_authorization(**overrides) -> OAuthPendingAuthorization:
    """A pending authorization as MockOAuthIntegration would hold it, with any field overridden."""
    fields = {
        "state": "state-123",
        "verifier": "verifier-123",
        "client": OAuthClientCredentials(client_id="registered-once"),
        "token_endpoint": "https://provider.example.com/token",
        "redirect_uri": "http://testserver/callback",
    }
    return OAuthPendingAuthorization(**{**fields, **overrides})
