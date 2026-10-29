from pydantic import BaseModel, Field, model_validator

from .stop_reason import StopReason


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
        """A message to send to the agent."""
        return cls(text=text)

    @classmethod
    def stop(cls, reason: StopReason) -> "UserMessage":
        """A stop: the user is done, or gave up."""
        return cls(stop_reason=reason)

    @property
    def is_stop(self) -> bool:
        """Whether the user stops here rather than sending a message."""
        return self.stop_reason is not None
