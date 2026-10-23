from ..trace import Turn
from .base_user_simulator import BaseUserSimulator
from .user_message import UserMessage


class ScriptedUser(BaseUserSimulator):
    """Sends the case's turns in order, whatever the agent answers, and stops when they run out."""

    def next_message(self, turns: list[Turn]) -> UserMessage:
        if len(turns) < len(self.case.turns):
            return UserMessage.say(self.case.turns[len(turns)])
        return UserMessage.stop("done")
