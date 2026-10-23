from typing import Literal

from pydantic import BaseModel

StopReason = Literal["done", "gave_up"]


class UserMessage(BaseModel):
    """A simulator's next move: a message to send, or a stop with its reason."""

    text: str | None = None
    stop_reason: StopReason | None = None

    @classmethod
    def say(cls, text: str) -> "UserMessage":
        return cls(text=text)

    @classmethod
    def stop(cls, reason: StopReason) -> "UserMessage":
        return cls(stop_reason=reason)

    @property
    def is_stop(self) -> bool:
        return self.text is None
