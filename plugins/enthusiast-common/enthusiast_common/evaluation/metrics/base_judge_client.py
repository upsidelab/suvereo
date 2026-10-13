from abc import ABC, abstractmethod

from ..suite import ModelTarget


class BaseJudgeClient(ABC):
    """The model LLM-based metrics ask; the host implements it with the suite's judge model and tracks its cost."""

    @abstractmethod
    def complete(self, prompt: str, model: ModelTarget | None = None) -> str:
        """Ask the judge one question and return its text reply; model overrides the suite's judge for this call."""
