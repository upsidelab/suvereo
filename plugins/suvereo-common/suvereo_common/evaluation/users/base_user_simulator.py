from abc import ABC, abstractmethod

from suvereo_common.evaluation.base_model_client import BaseModelClient
from suvereo_common.evaluation.suite import ConversationEvalCase
from suvereo_common.evaluation.trace import Turn
from suvereo_common.evaluation.users.user_message import UserMessage


class BaseUserSimulator(ABC):
    """Plays the user in a conversation case; the runner sends its messages until it stops or max_turns is reached."""

    def __init__(self, case: ConversationEvalCase, llm: BaseModelClient | None = None):
        """``simulated_user`` holds the case's goal, persona, facts and params; a case with fixed user messages has
        none. ``llm`` is the suite's user model, for simulators that ask one."""
        self.case = case
        self.simulated_user = case.simulated_user
        self.llm = llm

    @abstractmethod
    def next_message(self, turns: list[Turn]) -> UserMessage:
        """The next user message given the turns so far, or a stop."""
