from http.cookies import SimpleCookie

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from account.authentication import AUTH_TOKEN_COOKIE_NAME
from account.models import AuthToken


class AuthTokenCookieMiddleware:
    """ASGI middleware resolving scope["user"] from the auth_token cookie.

    Replaces channels.auth.AuthMiddlewareStack, which resolves scope["user"]
    from Django's session framework - this app doesn't use Django sessions
    for its own authentication at all, so AuthMiddlewareStack would never
    resolve a real user here.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope["user"] = await self._resolve_user(scope)
        return await self.app(scope, receive, send)

    async def _resolve_user(self, scope):
        headers = dict(scope.get("headers", []))
        cookie_header = headers.get(b"cookie", b"").decode()
        cookies = SimpleCookie()
        cookies.load(cookie_header)
        if AUTH_TOKEN_COOKIE_NAME not in cookies:
            return AnonymousUser()
        return await self._user_for_key(cookies[AUTH_TOKEN_COOKIE_NAME].value)

    @database_sync_to_async
    def _user_for_key(self, key):
        token = AuthToken.get_valid_token(key)
        return token.user if token else AnonymousUser()
