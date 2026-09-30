import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from agent.models import Conversation

CLOSE_UNAUTHENTICATED = 4401
CLOSE_FORBIDDEN = 4403


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=CLOSE_UNAUTHENTICATED)
            return
        if not await self._is_conversation_visible(user):
            await self.close(code=CLOSE_FORBIDDEN)
            return

        self.group_name = f"conversation_{self.conversation_id}"

        # Join the conversation group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    @database_sync_to_async
    def _is_conversation_visible(self, user) -> bool:
        return Conversation.objects.visible_to(user).filter(id=self.conversation_id).exists()

    async def disconnect(self, close_code):
        if not hasattr(self, "group_name"):
            return
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def chat_message(self, event):
        event_type = event.get("event")
        handlers = {
            "start": self.handle_start,
            "stream": self.handle_stream,
            "end": self.handle_end,
            "message_created": self.handle_message_created,
            "tool_call": self.handle_tool_call,
            "tool_done": self.handle_tool_done,
            "error": self.handle_error,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler(event)

    async def handle_start(self, event):
        await self.send(json.dumps({"event": "on_parser_start", "data": {"run_id": event.get("run_id")}}))

    async def handle_stream(self, event):
        await self.send(json.dumps({"event": "on_parser_stream", "data": {"chunk": event.get("token")}}))

    async def handle_end(self, event):
        await self.send(json.dumps({"event": "on_parser_end", "data": {"output": event.get("output")}}))

    async def handle_message_created(self, event):
        await self.send(json.dumps({"event": "message_id", "data": {"output": event.get("answer_id")}}))

    async def handle_tool_call(self, event):
        await self.send(json.dumps({"event": "tool_call", "data": {"tool_name": event.get("tool_name")}}))

    async def handle_tool_done(self, event):
        await self.send(json.dumps({"event": "tool_done", "data": {}}))

    async def handle_error(self, event):
        await self.send(json.dumps({"event": "error", "data": {"output": event.get("output")}}))
