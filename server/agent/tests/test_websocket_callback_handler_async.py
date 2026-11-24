import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, LLMResult
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


class TestConversationWebSocketCallbackHandlerContentBlocks:
    """Models that stream content blocks (e.g. OpenAI's Responses API) hand ``on_llm_new_token`` a list of
    blocks instead of a string; only their text may reach the WebSocket."""

    @staticmethod
    def _stream(handler, blocks: list) -> None:
        handler.on_llm_new_token(blocks, chunk=ChatGenerationChunk(message=AIMessageChunk(content=blocks)))

    @patch("agent.core.callbacks.base_websocket_handler.get_channel_layer")
    def test_only_text_of_content_blocks_is_streamed(self, mock_get_channel_layer):
        channel_layer = MagicMock()
        channel_layer.group_send = AsyncMock()
        mock_get_channel_layer.return_value = channel_layer
        handler = ConversationWebSocketCallbackHandler(conversation_id=1)

        self._stream(handler, [{"type": "function_call", "name": "ping_tool", "arguments": "", "index": 0}])
        self._stream(handler, [{"type": "text", "text": "", "index": 0}])
        self._stream(handler, [{"type": "text", "text": "hello", "index": 0}])
        self._stream(handler, [{"type": "text", "text": " there", "index": 0}])

        streamed = [call.args[1]["token"] for call in channel_layer.group_send.await_args_list]
        assert streamed == ["hello", " there"]


class TestConversationWebSocketCallbackHandlerMessageEvents:
    def _build_handler(self, mock_get_channel_layer):
        channel_layer = MagicMock()
        channel_layer.group_send = AsyncMock()
        mock_get_channel_layer.return_value = channel_layer
        return ConversationWebSocketCallbackHandler(conversation_id=1), channel_layer

    @staticmethod
    def _events(channel_layer):
        return [call.args[1] for call in channel_layer.group_send.await_args_list]

    @pytest.mark.parametrize(
        "message",
        [
            AIMessage(content="Let me check.", tool_calls=[{"id": "call_1", "name": "ping_tool", "args": {}}]),
            AIMessage(content="Done."),
        ],
        ids=["tool call narration", "final answer"],
    )
    @patch("agent.core.callbacks.base_websocket_handler.get_channel_layer")
    def test_a_model_call_that_streamed_text_ends_its_message(self, mock_get_channel_layer, message):
        handler, channel_layer = self._build_handler(mock_get_channel_layer)
        run_id = uuid4()

        handler.on_llm_new_token(message.text, run_id=run_id)
        handler.on_llm_end(LLMResult(generations=[[ChatGeneration(message=message)]]), run_id=run_id)

        assert [event["event"] for event in self._events(channel_layer)] == ["stream", "message_end"]

    @patch("agent.core.callbacks.base_websocket_handler.get_channel_layer")
    def test_a_model_call_that_fails_while_streaming_ends_its_message(self, mock_get_channel_layer):
        handler, channel_layer = self._build_handler(mock_get_channel_layer)
        run_id = uuid4()

        handler.on_llm_new_token("Let me check the cat", run_id=run_id)
        handler.on_llm_error(ConnectionError("stream dropped"), run_id=run_id)

        assert [event["event"] for event in self._events(channel_layer)] == ["stream", "message_end"]

    @patch("agent.core.callbacks.base_websocket_handler.get_channel_layer")
    def test_a_model_call_that_streamed_nothing_sends_no_message_end(self, mock_get_channel_layer):
        handler, channel_layer = self._build_handler(mock_get_channel_layer)

        handler.on_llm_end(
            LLMResult(generations=[[ChatGeneration(message=AIMessage(content="Done."))]]), run_id=uuid4()
        )

        assert self._events(channel_layer) == []
