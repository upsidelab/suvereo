import logging
from pathlib import Path

from enthusiast_common.evaluation.metrics import BaseMetric, MetricContext, MetricError, MetricRegistry, MetricResult
from enthusiast_common.evaluation.metrics.auto import auto_metrics_for
from enthusiast_common.evaluation.suite import MetricConfig, PassThreshold, SuiteKind

from .run_result import ThresholdResult

logger = logging.getLogger(__name__)

BOOL_THRESHOLD = PassThreshold(equals=True)


class RunScorer:
    """Measures a run's auto metrics (those of the suite's kind) and configured ones, and checks the configured ones'
    pass thresholds; bools default to equals: true."""

    def __init__(self, base_dir: Path, kind: SuiteKind = "execution", registry: MetricRegistry | None = None):
        self.base_dir = base_dir
        self.auto_metrics = auto_metrics_for(kind)
        self.registry = registry or MetricRegistry()

    def score(
        self, configs: list[MetricConfig], context: MetricContext
    ) -> tuple[dict[str, MetricResult], dict[str, ThresholdResult]]:
        """Measure the auto metrics and each configured metric, and check pass thresholds: a configured one, or
        equals: true for a bool metric. A metric that cannot be built has no value and misses its threshold, as a
        broken check never passes."""
        results = {metric.NAME: self._measure_safely(metric(), context) for metric in self.auto_metrics}
        thresholds = {}
        for config in configs:
            try:
                metric = self.registry.build_metric(config, self.base_dir)
            except MetricError as e:
                results[config.name] = MetricResult(value=None, details={"error": str(e)})
                thresholds[config.name] = ThresholdResult(passed=False, required=config.required)
                continue
            results[config.name] = self._measure_safely(metric, context)
            threshold = config.pass_threshold or (BOOL_THRESHOLD if metric.VALUE_TYPE == "bool" else None)
            if threshold is not None:
                thresholds[config.name] = ThresholdResult(
                    passed=threshold.passes(results[config.name].value), required=config.required
                )
        return results, thresholds

    def scores_for_unfinished_run(
        self, configs: list[MetricConfig], context: MetricContext, reason: str
    ) -> tuple[dict[str, MetricResult], dict[str, ThresholdResult]]:
        """For a run that never ran: the auto metrics, and each configured metric with no value and a missed
        threshold."""
        results = {metric.NAME: self._measure_safely(metric(), context) for metric in self.auto_metrics}
        results |= {config.name: MetricResult(value=None, details={"reason": reason}) for config in configs}
        thresholds = {config.name: ThresholdResult(passed=False, required=config.required) for config in configs}
        return results, thresholds

    @staticmethod
    def _measure_safely(metric: BaseMetric, context: MetricContext) -> MetricResult:
        try:
            return metric.measure(context)
        except Exception as e:
            logger.warning("Metric %s failed on case %s", metric.name, context.case.id, exc_info=True)
            return MetricResult(value=None, details={"error": f"{type(e).__name__}: {e}"})
