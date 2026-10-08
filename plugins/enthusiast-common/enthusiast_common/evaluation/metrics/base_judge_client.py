from abc import ABC, abstractmethod


class BaseJudgeClient(ABC):
    """The model LLM-based metrics ask; the host implements it with the suite's judge model and tracks its cost."""

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Ask the judge model one question.

        Args:
            prompt: The full prompt, material to judge included.

        Returns:
            The model's text reply.
        """
