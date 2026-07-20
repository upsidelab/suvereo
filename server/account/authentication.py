from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class ServiceAccountTokenAuthentication(TokenAuthentication):
    """Token authentication restricted to service accounts.

    Human users authenticate via the session cookie (see LoginView). A Token
    row existing for a non-service-account user — e.g. one left over from
    before this refactor, or created by a future bug — must never grant
    access on its own.
    """

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if not user.is_service_account:
            raise AuthenticationFailed("Token authentication is only available for service accounts.")
        return user, token
