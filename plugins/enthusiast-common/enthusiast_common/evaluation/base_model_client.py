from abc import ABC, abstractmethod

from .suite import ModelTarget


class BaseModelClient(ABC):
    """A model the evaluation asks besides the agent, e.g. a judge or a simulated user; the host implements it and
    tracks its cost."""

    @abstractmethod
    def complete(self, prompt: str, model: ModelTarget | None = None) -> str:
        """Ask one question and return the text reply; model overrides the client's own model for this call."""
