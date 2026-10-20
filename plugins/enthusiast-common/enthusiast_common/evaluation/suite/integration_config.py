from typing import Any

from pydantic import Field, model_validator

from .base import EvalModel


class IntegrationConfig(EvalModel):
    """A mock integration standing in for an external system."""

    class_path: str | None = Field(default=None, alias="class", description="Dotted path to a mock integration.")
    interface: str | None = Field(default=None, description="Dotted path to an interface to mock with no code.")
    config: dict[str, Any] = Field(default={}, description="The mock's 'behaviour' per method and its 'data'.")

    @model_validator(mode="after")
    def _exactly_one_target(self) -> "IntegrationConfig":
        if (self.class_path is None) == (self.interface is None):
            raise ValueError("Set exactly one of 'class' (a mock integration) or 'interface' (a declarative mock).")
        return self

    @property
    def key(self) -> str:
        """The class or interface path; a case's override applies to the suite integration with the same key."""
        return self.class_path or self.interface
