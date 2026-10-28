from pydantic import Field, field_validator, model_validator

from .eval_case import EvalCase
from .simulated_user_config import SimulatedUserConfig


class ConversationEvalCase(EvalCase):
    """A case of a conversation suite: the agent chats with fixed user messages or with a simulated user."""

    user_messages: list[str] = Field(default=[], description="Sent in order, whatever the agent answers.")
    simulated_user: SimulatedUserConfig | None = Field(
        default=None, description="Writes the user's side, answering the agent; an LLM or a custom simulator."
    )

    @field_validator("user_messages")
    @classmethod
    def _messages_are_not_blank(cls, messages: list[str]) -> list[str]:
        if any(not message.strip() for message in messages):
            raise ValueError("A user message must have text.")
        return messages

    @model_validator(mode="after")
    def _one_kind_of_user(self) -> "ConversationEvalCase":
        if bool(self.user_messages) == (self.simulated_user is not None):
            raise ValueError("Set either 'user_messages' (fixed messages) or 'simulated_user'.")
        return self
