from typing import Any

from langchain_core.outputs import ChatGenerationChunk, GenerationChunk

from agent.core.callbacks.base_websocket_handler import BaseWebSocketHandler


class ConversationWebSocketCallbackHandler(BaseWebSocketHandler):
    """Streams LLM tokens and tool events to the WebSocket group for a conversation."""

    def on_llm_new_token(
        self, token: str | list, *, chunk: GenerationChunk | ChatGenerationChunk | None = None, **kwargs
    ) -> None:
        text = chunk.message.text if isinstance(chunk, ChatGenerationChunk) else token
        if not text or not isinstance(text, str):
            return
        self.send_message({"type": "chat_message", "event": "stream", "token": text})

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs) -> None:
        tool_name = serialized.get("name", "tool")
        self.send_message({"type": "chat_message", "event": "tool_call", "tool_name": tool_name})

    def on_tool_end(self, output: Any, **kwargs) -> None:
        self.send_message({"type": "chat_message", "event": "tool_done"})

    def on_tool_error(self, error: Any, **kwargs) -> None:
        self.send_message({"type": "chat_message", "event": "tool_done"})
