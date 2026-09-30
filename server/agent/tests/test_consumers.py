import pytest
from asgiref.sync import async_to_sync
from channels.routing import URLRouter
from channels.security.websocket import OriginValidator
from channels.testing import WebsocketCommunicator
from django.core.cache import cache
from django.test import override_settings
from model_bakery import baker

import agent.routing
from account.models import User
from account.services import WebSocketTicketService
from agent.consumers import CLOSE_FORBIDDEN, CLOSE_UNAUTHENTICATED
from agent.ws_auth import TicketAuthMiddleware

pytestmark = pytest.mark.django_db

FRONTEND_ORIGIN = "http://frontend.test"

application = OriginValidator(
    TicketAuthMiddleware(URLRouter(agent.routing.websocket_urlpatterns)),
    [FRONTEND_ORIGIN],
)


@pytest.fixture(autouse=True)
def in_memory_backends():
    with override_settings(
        CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    ):
        yield
        cache.clear()


def connect(conversation_id, ticket=None, origin=FRONTEND_ORIGIN):
    async def run():
        path = f"/ws/chat/{conversation_id}/" + (f"?ticket={ticket}" if ticket else "")
        headers = [(b"origin", origin.encode())] if origin else []
        communicator = WebsocketCommunicator(application, path, headers=headers)
        connected, code = await communicator.connect()
        await communicator.disconnect()
        return connected, code

    return async_to_sync(run)()


class TestChatConsumerAuthentication:
    def test_valid_ticket_for_own_conversation_is_accepted(self, user, conversation):
        ticket = WebSocketTicketService().issue(user)

        assert connect(conversation.id, ticket) == (True, None)

    def test_missing_ticket_is_rejected(self, conversation):
        assert connect(conversation.id) == (False, CLOSE_UNAUTHENTICATED)

    def test_unknown_ticket_is_rejected(self, conversation):
        assert connect(conversation.id, "not-a-ticket") == (False, CLOSE_UNAUTHENTICATED)

    def test_ticket_is_single_use(self, user, conversation):
        ticket = WebSocketTicketService().issue(user)
        connect(conversation.id, ticket)

        assert connect(conversation.id, ticket) == (False, CLOSE_UNAUTHENTICATED)

    def test_expired_ticket_is_rejected(self, user, conversation):
        ticket = WebSocketTicketService().issue(user)
        cache.delete(f"{WebSocketTicketService.KEY_PREFIX}{ticket}")

        assert connect(conversation.id, ticket) == (False, CLOSE_UNAUTHENTICATED)

    def test_inactive_user_ticket_is_rejected(self, user, conversation):
        ticket = WebSocketTicketService().issue(user)
        user.is_active = False
        user.save()

        assert connect(conversation.id, ticket) == (False, CLOSE_UNAUTHENTICATED)

    def test_other_users_conversation_is_rejected(self, conversation):
        other_user = baker.make(User)
        ticket = WebSocketTicketService().issue(other_user)

        assert connect(conversation.id, ticket) == (False, CLOSE_FORBIDDEN)

    def test_disallowed_origin_is_rejected(self, user, conversation):
        ticket = WebSocketTicketService().issue(user)

        connected, _ = connect(conversation.id, ticket, origin="http://evil.test")

        assert connected is False
