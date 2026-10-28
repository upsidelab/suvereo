from enthusiast_common.evaluation.base_model_client import BaseModelClient
from enthusiast_common.evaluation.chat_message import ChatMessage
from enthusiast_common.evaluation.suite import ModelTarget


class ScriptedJudge(BaseModelClient):
    """Replies with prepared answers in turn, the last one repeating, and keeps what it was sent: each conversation,
    its last message as the prompt, the system prompt and the model."""

    def __init__(self, *replies: str):
        self.replies = list(replies)
        self.conversations: list[list[ChatMessage]] = []
        self.prompts: list[str] = []
        self.systems: list[str | None] = []
        self.models: list[ModelTarget | None] = []

    def chat(self, messages: list[ChatMessage], system: str | None = None, model: ModelTarget | None = None) -> str:
        self.conversations.append(messages)
        self.prompts.append(messages[-1].text)
        self.systems.append(system)
        self.models.append(model)
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
