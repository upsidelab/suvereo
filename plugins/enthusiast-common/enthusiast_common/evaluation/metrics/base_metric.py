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
    """Something measured on every run: a number, a bool or a label. Gates and aggregation are the runner's job.

    A subclass declares ``NAME`` (how suites refer to it), ``VALUE_TYPE`` (``number``, ``bool`` or ``label``) and,
    when it takes parameters, a ``PARAMS`` model; its docstring is what ``listevalmetrics`` shows.
    """

    __abstract__ = True

    NAME: ClassVar[str]
    VALUE_TYPE: ClassVar[str]
    PARAMS: ClassVar[type[BaseModel]] = NoParams

    def __init__(self, params: dict[str, Any] | None = None, name: str | None = None, base_dir: Path | None = None):
        """Create a configured metric.

        Args:
            params: The suite's ``params``, validated against ``PARAMS``.
            name: The instance's name in reports; defaults to ``NAME``.
            base_dir: The suite's directory, which relative paths in params resolve against; the working
                directory when omitted.

        Raises:
            MetricConfigError: If ``params`` do not fit ``PARAMS``.
        """
        try:
            self.params = self.PARAMS.model_validate(params or {}, context={BASE_DIR: base_dir or Path.cwd()})
        except ValidationError as e:
            raise MetricConfigError(f"Invalid params for metric '{name or self.NAME}': {e}") from e
        self.name = name or self.NAME

    @abstractmethod
    def measure(self, context: MetricContext) -> MetricResult:
        """Measure one run.

        Args:
            context: The run's trace, its case, and the runner's figures for it.

        Returns:
            The value, plus any details (diffs, reasoning) and components (e.g. precision, recall).
        """
