from pydantic import BaseModel, ConfigDict


class MockRaise(BaseModel):
    """An error a mock raises: a name known to the mock, a builtin exception, or a dotted class path."""

    model_config = ConfigDict(extra="forbid")

    error: str
    message: str = ""
