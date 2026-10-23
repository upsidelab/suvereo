from typing import Literal

from pydantic import BaseModel, Field, model_validator

StopReason = Literal["done", "gave_up"]


class UserMessage(BaseModel):
    """A simulator's next move: a message to send, or a stop with its reason; exactly one of the two."""

    text: str | None = Field(default=None, min_length=1)
    stop_reason: StopReason | None = None

    @model_validator(mode="after")
    def _a_message_or_a_stop(self) -> "UserMessage":
        if (self.text is None) == (self.stop_reason is None):
            raise ValueError("Set exactly one of 'text' (a message to send) or 'stop_reason' (a stop).")
        return self

    @classmethod
    def say(cls, text: str) -> "UserMessage":
        return cls(text=text)

    @classmethod
    def stop(cls, reason: StopReason) -> "UserMessage":
        return cls(stop_reason=reason)

    @property
    def is_stop(self) -> bool:
        return self.stop_reason is not None
