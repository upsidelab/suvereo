from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser

from account.services import WebSocketTicketService


class TicketAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> Any:
        ticket = parse_qs(scope.get("query_string", b"").decode()).get("ticket", [None])[0]
        user = await self._redeem(ticket) if ticket else None
        scope = dict(scope, user=user or AnonymousUser())
        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def _redeem(self, ticket: str) -> AbstractBaseUser | None:
        return WebSocketTicketService().redeem(ticket)
