from abc import ABC, abstractmethod

from ..suite import ConversationEvalCase
from ..trace import Turn
from .user_message import UserMessage


class BaseUserSimulator(ABC):
    """Plays the user in a conversation case; the runner sends its messages until it stops or max_turns is reached."""

    def __init__(self, case: ConversationEvalCase):
        """``simulated_user`` holds the case's goal, persona and params; a case with fixed user messages has none."""
        self.case = case
        self.simulated_user = case.simulated_user

    @abstractmethod
    def next_message(self, turns: list[Turn]) -> UserMessage:
        """The next user message given the turns so far, or a stop."""
