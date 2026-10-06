from typing import Any

from pydantic import BaseModel


class ToolCall(BaseModel):
    """One tool invocation by the agent."""

    run_id: str
    parent_run_id: str | None = None
    name: str
    args: dict[str, Any] = {}
    output: str | None = None
    error: str | None = None
    duration_s: float | None = None
