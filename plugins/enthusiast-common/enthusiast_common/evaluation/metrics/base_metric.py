from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, ValidationError

from .errors import MetricConfigError
from .metric_context import MetricContext
from .metric_meta import MetricMeta
from .metric_result import MetricResult
from .no_params import NoParams

#: The validation-context key under which params find the suite directory.
BASE_DIR = "base_dir"


class BaseMetric(ABC, metaclass=MetricMeta):
    """Something measured on every run; declares NAME, VALUE_TYPE (number, bool or label) and optionally PARAMS."""

    __abstract__ = True

    NAME: ClassVar[str]
    VALUE_TYPE: ClassVar[str]
    PARAMS: ClassVar[type[BaseModel]] = NoParams

    def __init__(self, params: dict[str, Any] | None = None, name: str | None = None, base_dir: Path | None = None):
        """Validate params against PARAMS (relative paths resolve against base_dir); raises MetricConfigError."""
        try:
            self.params = self.PARAMS.model_validate(params or {}, context={BASE_DIR: base_dir or Path.cwd()})
        except ValidationError as e:
            raise MetricConfigError(f"Invalid params for metric '{name or self.NAME}': {e}") from e
        self.name = name or self.NAME

    @abstractmethod
    def measure(self, context: MetricContext) -> MetricResult:
        """Measure one run: its value, plus details (diffs, reasoning) and components (e.g. precision, recall)."""
