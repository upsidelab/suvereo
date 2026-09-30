from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

from account.services import WebSocketTicketService


class TicketAuthMiddleware(BaseMiddleware):
    """Authenticates a WebSocket connection by redeeming the single-use `ticket` from its query string.

    Sets `scope["user"]` to the ticket's user, or to `AnonymousUser` when the ticket is missing or invalid.
    """

    async def __call__(self, scope, receive, send):
        ticket = parse_qs(scope.get("query_string", b"").decode()).get("ticket", [None])[0]
        user = await self._redeem(ticket) if ticket else None
        scope = dict(scope, user=user or AnonymousUser())
        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def _redeem(self, ticket: str):
        return WebSocketTicketService().redeem(ticket)
