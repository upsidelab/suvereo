from typing import Any

from pydantic import Field, model_validator

from .base import EvalModel

DEFAULT_VARIANT = "default"


class PromptVariant(EvalModel):
    """A variation compared against the agent's own prompt, the implicit 'default' variant."""

    name: str
    system_prompt_file: str | None = Field(default=None, description="Replaces the system prompt; suite-relative.")
    agent_config: dict[str, Any] | None = Field(default=None, description="Deep-merged over the agent's config.")

    @model_validator(mode="after")
    def _changes_something(self) -> "PromptVariant":
        if self.name == DEFAULT_VARIANT:
            raise ValueError(f"'{DEFAULT_VARIANT}' is reserved for the agent's own prompt.")
        if self.system_prompt_file is None and not self.agent_config:
            raise ValueError(f"Variant '{self.name}' sets neither 'system_prompt_file' nor 'agent_config'.")
        return self
