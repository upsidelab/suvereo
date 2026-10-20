from typing import Any

from pydantic import BaseModel


class MetricResult(BaseModel):
    """One metric's measurement of one run; a None value means the metric could not be measured for it."""

    value: float | bool | str | None
    details: dict[str, Any] = {}
    components: dict[str, float] = {}
    #: Each component is success (1) or failure (0), so reports show it in words.
    binary_components: bool = False
