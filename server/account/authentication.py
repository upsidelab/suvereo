from datetime import timedelta

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, CSRFCheck, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

from account.models import AuthToken

AUTH_TOKEN_COOKIE_NAME = "auth_token"
HUMAN_TOKEN_LIFETIME = timedelta(weeks=1)


class AuthTokenAuthentication(BaseAuthentication):
    """Authenticates via AuthToken, presented as an Authorization header
    (service accounts) or the auth_token cookie (human users). Same model
    and lookup for both, but only cookie-presented tokens are subject to
    CSRF re-validation, since only cookies are auto-attached to cross-site
    requests by the browser.
    """

    keyword = "Token"

    def authenticate(self, request):
        header_key = self._key_from_header(request)
        key = header_key or request.COOKIES.get(AUTH_TOKEN_COOKIE_NAME)
        if key is None:
            return None

        token = AuthToken.get_valid_token(key)
        if token is None:
            raise AuthenticationFailed("Invalid or expired token.")

        if header_key is not None and not token.user.is_service_account:
            raise AuthenticationFailed("Invalid or expired token.")

        if header_key is None:
            self._enforce_csrf(request)

        if token.expires_at is not None:
            token.expires_at = timezone.now() + HUMAN_TOKEN_LIFETIME
            token.save(update_fields=["expires_at"])

        return (token.user, token)

    def _enforce_csrf(self, request):
        def dummy_get_response(request):  # pragma: no cover
            return None

        check = CSRFCheck(dummy_get_response)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise PermissionDenied(f"CSRF Failed: {reason}")

    def _key_from_header(self, request):
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None
        if len(auth) != 2:
            raise AuthenticationFailed("Invalid token header.")
        try:
            return auth[1].decode()
        except UnicodeError:
            raise AuthenticationFailed("Invalid token header.")

    def authenticate_header(self, request):
        return self.keyword
