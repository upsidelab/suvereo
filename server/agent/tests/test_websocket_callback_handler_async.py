import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from agent.core.callbacks import ConversationWebSocketCallbackHandler


@tool
def ping_tool(value: str) -> str:
    """Return a canned response, so a tool run can be observed."""
    return "pong"


class TestConversationWebSocketCallbackHandlerUnderAsyncRun:
    """The handler is a *sync* callback handler that reaches the channel layer through
    ``async_to_sync``. Agents answering via ``aget_answer`` dispatch it from inside a running
    event loop, where ``async_to_sync`` raises if it ends up on the loop's own thread. These
    tests pin down that streaming and tool events still get through on the async path.
    """

    def _build_handler(self, mock_get_channel_layer):
        channel_layer = MagicMock()
        channel_layer.group_send = AsyncMock()
        mock_get_channel_layer.return_value = channel_layer
        return ConversationWebSocketCallbackHandler(conversation_id=1), channel_layer

    @patch("agent.core.callbacks.base_websocket_handler.get_channel_layer")
    def test_tool_events_reach_the_channel_layer_during_an_async_run(self, mock_get_channel_layer):
        handler, channel_layer = self._build_handler(mock_get_channel_layer)

        asyncio.run(ping_tool.ainvoke({"value": "hi"}, config={"callbacks": [handler]}))

        events = [call.args[1]["event"] for call in channel_layer.group_send.await_args_list]
        assert "tool_call" in events
        assert "tool_done" in events

    @patch("agent.core.callbacks.base_websocket_handler.get_channel_layer")
    def test_streamed_tokens_reach_the_channel_layer_during_an_async_run(self, mock_get_channel_layer):
        handler, channel_layer = self._build_handler(mock_get_channel_layer)
        model = GenericFakeChatModel(messages=iter([AIMessage(content="hello there")]))

        async def stream_answer():
            return [chunk async for chunk in model.astream("hi", config={"callbacks": [handler]})]

        asyncio.run(stream_answer())

        streamed = [
            call.args[1]["token"]
            for call in channel_layer.group_send.await_args_list
            if call.args[1]["event"] == "stream"
        ]
        assert "".join(streamed) == "hello there"
