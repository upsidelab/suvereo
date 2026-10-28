from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MockCall(BaseModel):
    """One call a mock received in place of an external system."""

    method: str
    args: list[Any] = []
    kwargs: dict[str, Any] = {}
    #: Every argument by parameter name, defaults included and ``**kwargs`` flattened; empty if binding failed.
    arguments: dict[str, Any] = {}
    result: Any = None
    error: str | None = None
    started_at: datetime
    duration_ms: float = 0.0
