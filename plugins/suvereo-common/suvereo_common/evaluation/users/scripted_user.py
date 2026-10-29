from ..trace import StopReason, Turn
from .base_user_simulator import BaseUserSimulator
from .user_message import UserMessage


class ScriptedUser(BaseUserSimulator):
    """Sends the case's user messages in order, whatever the agent answers, and stops when they run out."""

    def next_message(self, turns: list[Turn]) -> UserMessage:
        if len(turns) < len(self.case.user_messages):
            return UserMessage.say(self.case.user_messages[len(turns)])
        return UserMessage.stop(StopReason.DONE)
