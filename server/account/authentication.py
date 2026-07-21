from datetime import timedelta

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from account.models import AuthToken

AUTH_TOKEN_COOKIE_NAME = "auth_token"
HUMAN_TOKEN_LIFETIME = timedelta(weeks=1)


class AuthTokenAuthentication(BaseAuthentication):
    """Authenticates via AuthToken, presented as an Authorization header
    (service accounts) or the auth_token cookie (human users). One model,
    one check, regardless of caller.
    """

    keyword = "Token"

    def authenticate(self, request):
        key = self._key_from_header(request) or request.COOKIES.get(AUTH_TOKEN_COOKIE_NAME)
        if key is None:
            return None

        try:
            token = AuthToken.objects.select_related("user").get(key=key)
        except AuthToken.DoesNotExist:
            raise AuthenticationFailed("Invalid token.")

        if token.is_expired():
            raise AuthenticationFailed("Token has expired.")

        if not token.user.is_active:
            raise AuthenticationFailed("User inactive or deleted.")

        if token.expires_at is not None:
            token.expires_at = timezone.now() + HUMAN_TOKEN_LIFETIME
            token.save(update_fields=["expires_at"])

        return (token.user, token)

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
