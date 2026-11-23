from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, GenerationChunk, LLMResult

from agent.core.callbacks.base_websocket_handler import BaseWebSocketHandler


class ConversationWebSocketCallbackHandler(BaseWebSocketHandler):
    """Streams LLM tokens and tool events to the WebSocket group for a conversation."""

    def on_llm_new_token(
        self, token: str | list, *, chunk: GenerationChunk | ChatGenerationChunk | None = None, **kwargs: Any
    ) -> None:
        text = chunk.message.text if isinstance(chunk, ChatGenerationChunk) else token
        if not text or not isinstance(text, str):
            return
        self.send_message({"type": "chat_message", "event": "stream", "token": text})

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        if self._requests_tool_calls(response):
            self.send_message({"type": "chat_message", "event": "tool_call_narration_end"})

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs: Any) -> None:
        tool_name = serialized.get("name", "tool")
        self.send_message({"type": "chat_message", "event": "tool_call", "tool_name": tool_name})

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        self.send_message({"type": "chat_message", "event": "tool_done"})

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        self.send_message({"type": "chat_message", "event": "tool_done"})

    @staticmethod
    def _requests_tool_calls(response: LLMResult) -> bool:
        return any(
            isinstance(generation, ChatGeneration)
            and isinstance(generation.message, AIMessage)
            and bool(generation.message.tool_calls)
            for generations in response.generations
            for generation in generations
        )
