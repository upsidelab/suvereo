from typing import Any

from pydantic import BaseModel


class MetricResult(BaseModel):
    """One metric's measurement of one run; a None value means the metric could not be measured for it."""

    value: float | bool | str | None
    details: dict[str, Any] = {}
    components: dict[str, float] = {}
