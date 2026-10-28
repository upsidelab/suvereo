from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MockIntegrationConfig(BaseModel):
    """A mock integration's configuration, as written under an integration's ``config`` in a suite."""

    model_config = ConfigDict(extra="forbid")

    behaviour: dict[str, Any] = Field(default={}, description="Per method name, a behaviour or a list of them.")
    data: dict[str, Any] = Field(default={}, description="Read by stateful mocks, e.g. a catalog.")
    strict: bool = Field(default=False, description="Calls no behaviour answers raise instead of returning None.")
