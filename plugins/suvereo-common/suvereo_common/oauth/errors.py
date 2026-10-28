"""Failures raised while taking a provider through an OAuth flow."""


class OAuthError(Exception):
    """Raised when a server cannot be taken through the OAuth flow."""


class NoAuthorizationRequired(OAuthError):
    """Raised when a server serves its resource without asking for a token."""
