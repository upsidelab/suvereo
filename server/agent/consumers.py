import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from agent.models import Conversation


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4401)
            return

        conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        has_access = await self._user_has_conversation_access(user, conversation_id)
        if not has_access:
            await self.close(code=4403)
            return

        self.conversation_id = conversation_id
        self.group_name = f"conversation_{self.conversation_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    @database_sync_to_async
    def _user_has_conversation_access(self, user, conversation_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return False
        return user.has_dataset_access(conversation.data_set)

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
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

