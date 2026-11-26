from typing import Any, Dict, Optional

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage, messages_from_dict
from suvereo_common.repositories import BaseConversationRepository

from agent.models import Message

SYSTEM_NOTICE_TEMPLATE = "[Notice shown to the user: {text}]"
NOTICE_ORIGIN = {"origin": "notice"}
REFUSED_ANSWER = "I can't help with that request."
EMPTY_ANSWER = "I couldn't come up with an answer. Please try rephrasing your message."
# Gemini block reasons and the OpenAI/Azure content filter, as reported in finish_reason.
FILTERED_FINISH_REASONS = {
    "content_filter",
    "SAFETY",
    "PROHIBITED_CONTENT",
    "BLOCKLIST",
    "SPII",
    "RECITATION",
    "IMAGE_SAFETY",
}


class PersistentChatHistory(BaseChatMessageHistory):
    """
    A chat history implementation that persists messages in the database.
    Inject it into the agent to enable conversation persistence.
    """

    def __init__(self, conversation_repo: BaseConversationRepository, conversation_id: Any):
        self._conversation = conversation_repo.get_by_id(conversation_id)

    def add_messages(self, messages: list[BaseMessage]) -> None:
        """Persist a turn's messages, interleaving each tool call with its result.

        LLMs can invoke tools in parallel, producing an AIMessage with multiple tool_calls
        followed by multiple ToolMessages. This reorders them so each tool call is immediately
        followed by its result, which allows straightforward one-to-one reconstruction.

        A refused answer is stored as REFUSED_ANSWER and its whole turn as failed, so the turn is never
        sent to the model again: providers keep refusing a conversation that still contains the refused
        request. An empty answer is stored as EMPTY_ANSWER.
        """
        answer_failed = any(self._is_refused_answer(m) for m in messages)
        messages = [self._readable_answer(m) for m in messages]
        tool_messages = {m.tool_call_id: m for m in messages if isinstance(m, ToolMessage)}
        for message in messages:
            if isinstance(message, AIMessage) and message.tool_calls:
                for index, tool_call in enumerate(message.tool_calls):
                    narration = message.text if index == 0 else ""
                    self._store(AIMessage(content=narration, tool_calls=[tool_call]), answer_failed)
                    if tool_call["id"] in tool_messages:
                        self._store(tool_messages[tool_call["id"]], answer_failed)
            elif isinstance(message, ToolMessage):
                pass  # already persisted paired with its tool call above
            else:
                self._store(message, answer_failed)

    @classmethod
    def _readable_answer(cls, message: BaseMessage) -> BaseMessage:
        if not isinstance(message, AIMessage) or message.tool_calls:
            return message
        if cls._is_refused_answer(message):
            return message.model_copy(update={"content": REFUSED_ANSWER})
        if not message.text.strip():
            return message.model_copy(update={"content": EMPTY_ANSWER})
        return message

    @staticmethod
    def _is_refused_answer(message: BaseMessage) -> bool:
        if not isinstance(message, AIMessage) or message.tool_calls:
            return False
        metadata = message.response_metadata
        blocks = message.content if isinstance(message.content, list) else []
        return (
            metadata.get("stop_reason") == "refusal"
            or metadata.get("finish_reason") in FILTERED_FINISH_REASONS
            or bool(message.additional_kwargs.get("refusal"))
            or any(isinstance(block, dict) and block.get("type") == "refusal" for block in blocks)
        )

    def add_message(self, message: BaseMessage) -> None:
        """Persist a message to the database.

        AIMessages that contain tool calls are stored as INTERMEDIATE_STEP records.
        ToolMessages (tool results) are stored as FUNCTION records.
        All other standard message types are stored using their LangChain type string directly.
        """
        self._store(message, answer_failed=False)

    def _store(self, message: BaseMessage, answer_failed: bool) -> None:
        if isinstance(message, AIMessage) and message.tool_calls:
            self._create_intermediate_step_message(message, answer_failed)
        elif isinstance(message, ToolMessage):
            self.create_tool_message(message, answer_failed)
        else:
            self._conversation.messages.create(
                type=message.type,
                text=message.text,
                function_name=getattr(message, "name", None),
                answer_failed=answer_failed,
            )

    def _create_intermediate_step_message(self, message: AIMessage, answer_failed: bool = False) -> None:
        for index, tool_call in enumerate(message.tool_calls):
            self._conversation.messages.create(
                type=Message.MessageType.INTERMEDIATE_STEP,
                text=message.text.strip() if index == 0 else "",
                function_name=tool_call["name"],
                tool_call_id=tool_call["id"],
                tool_call_args=tool_call["args"],
                answer_failed=answer_failed,
            )

    def create_tool_message(self, message: ToolMessage, answer_failed: bool = False) -> None:
        self._conversation.messages.create(
            type=Message.MessageType.FUNCTION,
            text=message.text,
            function_name=message.name,
            tool_call_id=message.tool_call_id,
            answer_failed=answer_failed,
        )

    @property
    def messages(self) -> list[BaseMessage]:
        """The messages the conversation summary does not cover yet; all of them if there is no summary."""
        self._conversation.refresh_from_db(fields=["last_summarized_message_id"])
        return self.messages_after(self._conversation.last_summarized_message_id)

    def messages_after(self, message_id: Optional[int]) -> list[BaseMessage]:
        """Return messages after the given message ID, or all messages if it is None."""
        return self.to_langchain_messages(self.records_after(message_id))

    def records_after(self, message_id: Optional[int]) -> list[Message]:
        """Return the stored messages after the given message ID, or all of them if it is None, oldest first."""
        queryset = self._conversation.messages.filter(answer_failed=False).order_by("id")
        if message_id is not None:
            queryset = queryset.filter(id__gt=message_id)
        return list(queryset)

    @classmethod
    def to_langchain_messages(cls, records: list[Message]) -> list[BaseMessage]:
        """Convert stored messages one to one, in the same order."""
        return messages_from_dict([cls._parse_message_to_dict(record) for record in records])

    @staticmethod
    def _parse_message_to_dict(message: BaseMessage) -> Dict[str, Any]:
        data: Dict[str, Any] = {"content": message.text, "name": message.function_name}
        match message.type:
            case Message.MessageType.INTERMEDIATE_STEP:
                data = {
                    "content": message.text,
                    "tool_calls": [
                        {
                            "id": message.tool_call_id,
                            "name": message.function_name or "",
                            "args": message.tool_call_args or {},
                        }
                    ],
                }
            case Message.MessageType.FUNCTION:
                data = {"content": message.text, "name": message.function_name, "tool_call_id": message.tool_call_id}
            case Message.MessageType.NOTICE:
                return {
                    "type": "ai",
                    "data": {
                        "content": SYSTEM_NOTICE_TEMPLATE.format(text=message.text),
                        "additional_kwargs": dict(NOTICE_ORIGIN),
                    },
                }
        return {"type": message.langchain_type, "data": data}

    def clear(self) -> None:
        self._conversation.messages.all().delete()
