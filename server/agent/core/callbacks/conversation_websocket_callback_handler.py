from typing import Any
from uuid import UUID

from langchain_core.outputs import ChatGenerationChunk, GenerationChunk, LLMResult

from agent.core.callbacks.base_websocket_handler import BaseWebSocketHandler


class ConversationWebSocketCallbackHandler(BaseWebSocketHandler):
    """Streams LLM tokens and tool events to the WebSocket group for a conversation."""

    def __init__(self, conversation_id: int):
        super().__init__(conversation_id)
        self._streaming_runs: set[UUID] = set()

    def on_llm_new_token(
        self,
        token: str | list,
        *,
        chunk: GenerationChunk | ChatGenerationChunk | None = None,
        run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        text = chunk.message.text if isinstance(chunk, ChatGenerationChunk) else token
        if not text or not isinstance(text, str):
            return
        self._streaming_runs.add(run_id)
        self.send_message({"type": "chat_message", "event": "stream", "token": text})

    def on_llm_end(self, response: LLMResult, *, run_id: UUID | None = None, **kwargs: Any) -> None:
        self._end_streamed_message(run_id)

    def on_llm_error(self, error: BaseException, *, run_id: UUID | None = None, **kwargs: Any) -> None:
        self._end_streamed_message(run_id)

    def _end_streamed_message(self, run_id: UUID | None) -> None:
        if run_id in self._streaming_runs:
            self._streaming_runs.discard(run_id)
            self.send_message({"type": "chat_message", "event": "message_end"})

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs: Any) -> None:
        tool_name = serialized.get("name", "tool")
        self.send_message({"type": "chat_message", "event": "tool_call", "tool_name": tool_name})

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        self.send_message({"type": "chat_message", "event": "tool_done"})

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        self.send_message({"type": "chat_message", "event": "tool_done"})
