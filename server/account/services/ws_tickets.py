import secrets

from django.conf import settings
from django.core.cache import cache

from account.models import User


class WebSocketTicketService:
    """Issues and redeems single-use tickets that authenticate WebSocket connections."""

    KEY_PREFIX = "ws_ticket:"

    def issue(self, user: User) -> str:
        """Store a new ticket for `user` that expires after `WS_TICKET_TTL` seconds and return it."""
        ticket = secrets.token_urlsafe(32)
        cache.set(self._key(ticket), user.pk, timeout=settings.WS_TICKET_TTL)
        return ticket

    def redeem(self, ticket: str) -> User | None:
        """Consume `ticket` and return its active user, or `None` if it's unknown, expired or already used."""
        key = self._key(ticket)
        user_id = cache.get(key)
        if user_id is None or not cache.delete(key):
            return None
        return User.objects.filter(pk=user_id, is_active=True).first()

    def _key(self, ticket: str) -> str:
        return f"{self.KEY_PREFIX}{ticket}"
