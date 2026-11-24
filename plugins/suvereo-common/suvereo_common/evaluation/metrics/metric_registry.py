import importlib
from pathlib import Path

from suvereo_common.evaluation.metrics.base_metric import BaseMetric
from suvereo_common.evaluation.metrics.builtins import BUILTIN_METRICS
from suvereo_common.evaluation.metrics.errors import MetricNotFoundError
from suvereo_common.evaluation.suite import MetricConfig


class MetricRegistry:
    """Finds metric classes: built-ins by NAME (all of them unless a list is given), custom ones by dotted path."""

    def __init__(self, builtins: list[type[BaseMetric]] | None = None):
        self._builtins = {metric.NAME: metric for metric in (BUILTIN_METRICS if builtins is None else builtins)}

    def metric_class(self, metric_type: str) -> type[BaseMetric]:
        """The metric class for a built-in NAME or a dotted path; raises MetricNotFoundError."""
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

    def build_metric(self, config: MetricConfig, base_dir: Path | None = None) -> BaseMetric:
        """Instantiate a metric from its suite config; raises MetricNotFoundError or MetricConfigError."""
        return self.metric_class(config.type)(config.params, config.name, base_dir)
