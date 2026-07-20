import pytest
from asgiref.sync import async_to_sync
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from model_bakery import baker

from account.models import User
from agent.models import Conversation
from agent.models.agent import Agent
from agent.routing import websocket_urlpatterns
from catalog.models import DataSet


@pytest.mark.django_db
class TestChatConsumerAuth:
    def test_rejects_unauthenticated_connection(self):
        dataset = baker.make(DataSet)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        conversation = baker.make(Conversation, agent=agent, data_set=dataset)

        async def run():
            application = URLRouter(websocket_urlpatterns)
            communicator = WebsocketCommunicator(application, f"/ws/chat/{conversation.id}/")
            communicator.scope["user"] = AnonymousUser()
            connected, _ = await communicator.connect()
            assert connected is False
            await communicator.disconnect()

        async_to_sync(run)()

    def test_rejects_authenticated_user_without_dataset_access(self):
        dataset = baker.make(DataSet, users=[])
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        conversation = baker.make(Conversation, agent=agent, data_set=dataset)
        user = baker.make(User)

        async def run():
            application = URLRouter(websocket_urlpatterns)
            communicator = WebsocketCommunicator(application, f"/ws/chat/{conversation.id}/")
            communicator.scope["user"] = user
            connected, _ = await communicator.connect()
            assert connected is False
            await communicator.disconnect()

        async_to_sync(run)()


@pytest.mark.django_db
class TestWebSocketOriginValidation:
    def test_rejects_connection_from_untrusted_origin(self):
        from channels.security.websocket import OriginValidator

        dataset = baker.make(DataSet)
        agent = baker.make(Agent, deleted_at=None, dataset=dataset)
        conversation = baker.make(Conversation, agent=agent, data_set=dataset)
        user = baker.make(User)

        async def run():
            application = OriginValidator(
                URLRouter(websocket_urlpatterns), ["http://trusted-frontend.example"]
            )
            communicator = WebsocketCommunicator(
                application,
                f"/ws/chat/{conversation.id}/",
                headers=[(b"origin", b"http://evil.example")],
            )
            communicator.scope["user"] = user
            connected, _ = await communicator.connect()
            assert connected is False
            await communicator.disconnect()

        async_to_sync(run)()
