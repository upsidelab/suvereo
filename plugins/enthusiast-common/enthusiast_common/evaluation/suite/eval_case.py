from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator

from .base import EvalModel
from .integration_config import IntegrationConfig
from .metric_config import MetricConfig
from .user_config import UserConfig


class EvalCase(EvalModel):
    """One test case: what the agent gets (an execution's input, or a conversation's user), what is mocked, and what
    is expected."""

    id: str = Field(min_length=1)
    description: str = ""
    tags: list[str] = []
    input: dict[str, Any] = Field(default={}, description="Validated against the execution's INPUT_TYPE.")
    turns: list[str] = Field(default=[], description="A conversation's user messages, sent in order.")
    user: UserConfig | None = Field(default=None, description="A conversation's simulated user, or a custom one.")
    files: list[Path] = Field(default=[], description="Attached to the conversation; relative to the case file.")
    integrations: list[IntegrationConfig] = Field(default=[], description="Overrides of the suite's integrations.")
    expected: dict[str, Any] = Field(default={}, description="Free-form; metrics read the paths they need.")
    metrics: list[MetricConfig] = Field(default=[], description="Added to the suite's, or replacing them by name.")
    extra: dict[str, Any] = Field(default={}, description="Other CSV columns, for custom metrics.")

    @field_validator("turns")
    @classmethod
    def _turns_are_not_blank(cls, turns: list[str]) -> list[str]:
        if any(not turn.strip() for turn in turns):
            raise ValueError("A turn must have text.")
        return turns

    @model_validator(mode="after")
    def _one_way_to_drive_the_agent(self) -> "EvalCase":
        if sum([bool(self.input), bool(self.turns), self.user is not None]) > 1:
            raise ValueError(
                "Set only one of 'input' (an execution), 'turns' (a scripted user) or 'user' (a simulated one)."
            )
        return self
