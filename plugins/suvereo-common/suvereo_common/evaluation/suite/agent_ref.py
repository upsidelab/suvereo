from typing import Any

from pydantic import Field, model_validator

from .base import EvalModel


class AgentRef(EvalModel):
    """The agent under test: an existing agent, or an agent type run in a throwaway sandbox."""

    id: int | None = Field(default=None, description="An existing agent, used with its DataSet and integrations.")
    type: str | None = Field(default=None, description="An AGENT_KEY to run in a sandbox DataSet.")
    config: dict[str, Any] = Field(default={}, description="The sandbox agent's config; only with 'type'.")

    @model_validator(mode="after")
    def _exactly_one_target(self) -> "AgentRef":
        if (self.id is None) == (self.type is None):
            raise ValueError("Set exactly one of 'id' (an existing agent) or 'type' (a sandbox agent).")
        if self.id is not None and self.config:
            raise ValueError(
                "'config' applies only to a sandbox agent ('type'); use a variant to patch an existing one."
            )
        return self

    @property
    def is_sandbox(self) -> bool:
        return self.type is not None
