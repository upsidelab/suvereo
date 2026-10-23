from abc import ABC, abstractmethod

from ..suite import EvalCase
from ..trace import Turn
from .user_message import UserMessage


class BaseUserSimulator(ABC):
    """Plays the user in a conversation case; the runner sends its messages until it stops or max_turns is reached."""

    def __init__(self, case: EvalCase):
        """The case's ``user`` holds a simulated user's goal, persona and params; a scripted case has none."""
        self.case = case
        self.config = case.user

    @abstractmethod
    def next_message(self, turns: list[Turn]) -> UserMessage:
        """The next user message given the turns so far, or a stop."""
