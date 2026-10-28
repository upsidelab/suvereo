"""The shapes passed between the steps of an authorization-code flow."""

from pydantic import BaseModel


class OAuthClientCredentials(BaseModel):
    """Credentials an authorization server issued this deployment. Only ``client_id`` is promised by RFC 7591."""

    client_id: str
    client_secret: str | None = None


class OAuthTokens(BaseModel):
    """What a token endpoint returns for an exchanged code."""

    access_token: str
    token_type: str | None = None
    refresh_token: str | None = None
    expires_in: float | None = None


class OAuthPendingAuthorization(BaseModel):
    """What the callback needs to finish a PKCE code exchange begun by ``oauth_start``.

    Attributes:
        state: The value the provider echoes back, identifying this flow.
        verifier: The PKCE code verifier the challenge was derived from.
        client: The client the authorization URL was built for; the host keeps it for reuse.
        token_endpoint: Where the code is exchanged.
        redirect_uri: The redirect URI the code was issued for, sent again on exchange.
        resource: The RFC 8707 resource indicator, when the server asked for one.
        renewable: Whether the server says it will renew the token later.
    """

    state: str
    verifier: str
    client: OAuthClientCredentials
    token_endpoint: str
    redirect_uri: str
    resource: str | None = None
    renewable: bool = True


class OAuthAuthorizationRequest(BaseModel):
    """A begun flow: where to send the admin, and what to hold until they come back."""

    authorization_url: str
    pending: OAuthPendingAuthorization
