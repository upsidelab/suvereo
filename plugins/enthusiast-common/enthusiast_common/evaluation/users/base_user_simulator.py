from abc import ABC, abstractmethod

from ..suite import EvalCase, UserConfig
from ..trace import Turn
from .user_message import UserMessage


class BaseUserSimulator(ABC):
    """Plays the user in a conversation case; the runner sends its messages until it stops or max_turns is reached."""

    def __init__(self, config: UserConfig | None, case: EvalCase):
        self.config = config
        self.case = case

    @abstractmethod
    def next_message(self, turns: list[Turn]) -> UserMessage:
        """The next user message given the turns so far, or a stop."""
