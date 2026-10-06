from pathlib import Path
from typing import Any

from pydantic import Field

from .base import EvalModel
from .integration_config import IntegrationConfig
from .metric_config import MetricConfig


class EvalCase(EvalModel):
    """One test case: what the agent gets, what is mocked, and what is expected."""

    id: str = Field(min_length=1)
    description: str = ""
    tags: list[str] = []
    input: dict[str, Any] = Field(default={}, description="Validated against the execution's INPUT_TYPE.")
    files: list[Path] = Field(default=[], description="Attached to the conversation; relative to the case file.")
    integrations: list[IntegrationConfig] = Field(default=[], description="Overrides of the suite's integrations.")
    expected: dict[str, Any] = Field(default={}, description="Free-form; metrics read the paths they need.")
    metrics: list[MetricConfig] = Field(default=[], description="Added to the suite's, or replacing them by name.")
    extra: dict[str, Any] = Field(default={}, description="Other CSV columns, for custom metrics.")
