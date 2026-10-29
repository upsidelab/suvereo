from typing import Any

from pydantic import Field, model_validator

from .base import EvalModel


class SimulatedUserConfig(EvalModel):
    """The simulated user a conversation case is driven by: an LLM with a goal and persona, or a custom simulator."""

    goal: str = Field(default="", description="What the user wants out of the conversation.")
    persona: str = Field(default="", description="How the user talks, e.g. terse or vague.")
    max_turns: int = Field(default=10, ge=1, description="The turn limit; a conversation cut off here fails the run.")
    class_path: str | None = Field(default=None, alias="class", description="Dotted path to a custom simulator.")
    params: dict[str, Any] = Field(default={}, description="Passed to a custom simulator.")

    @model_validator(mode="after")
    def _has_a_goal_or_a_class(self) -> "SimulatedUserConfig":
        if not self.goal and self.class_path is None:
            raise ValueError("Set 'goal' for the simulated user, or 'class' for a custom simulator.")
        return self
