import importlib
from pathlib import Path

from ..suite import MetricConfig
from .base_metric import BaseMetric
from .builtins import BUILTIN_METRICS
from .errors import MetricNotFoundError


class MetricRegistry:
    """Finds metric classes: built-ins by NAME, custom ones by dotted path.

    Args:
        builtins: The metric classes looked up by NAME; the framework's built-ins when omitted.
    """

    def __init__(self, builtins: list[type[BaseMetric]] | None = None):
        self._builtins = {metric.NAME: metric for metric in (BUILTIN_METRICS if builtins is None else builtins)}

    def get(self, metric_type: str) -> type[BaseMetric]:
        """Find a metric class.

        Args:
            metric_type: A built-in's ``NAME``, or a dotted path to a ``BaseMetric`` subclass.

        Returns:
            The metric class.

        Raises:
            MetricNotFoundError: If it is neither.
        """
        if metric_type in self._builtins:
            return self._builtins[metric_type]
        module, _, attribute = metric_type.rpartition(".")
        try:
            candidate = getattr(importlib.import_module(module), attribute, None) if module else None
        except ImportError as e:
            raise MetricNotFoundError(f"Cannot import metric '{metric_type}'.") from e
        if not (isinstance(candidate, type) and issubclass(candidate, BaseMetric)):
            raise MetricNotFoundError(
                f"Unknown metric '{metric_type}'; use one of {', '.join(sorted(self._builtins))} or a dotted path."
            )
        return candidate

    def build(self, config: MetricConfig, base_dir: Path | None = None) -> BaseMetric:
        """Instantiate a metric from its suite configuration.

        Args:
            config: The metric's ``type``, ``name`` and ``params``.
            base_dir: The suite's directory, for relative paths in params.

        Returns:
            The configured metric, named as in the suite.

        Raises:
            MetricNotFoundError: If the type is unknown.
            MetricConfigError: If the params are invalid.
        """
        return self.get(config.type)(config.params, config.name, base_dir)

    def builtin_metrics(self) -> list[type[BaseMetric]]:
        """The built-in metric classes, by name."""
        return [self._builtins[name] for name in sorted(self._builtins)]
