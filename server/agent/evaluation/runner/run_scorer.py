import logging
from pathlib import Path

from enthusiast_common.evaluation.metrics import BaseMetric, MetricContext, MetricError, MetricRegistry, MetricResult
from enthusiast_common.evaluation.metrics.auto import AUTO_METRICS
from enthusiast_common.evaluation.suite import Gate, MetricConfig

from .run_result import GateResult

logger = logging.getLogger(__name__)

BOOL_GATE = Gate(equals=True)


class RunScorer:
    """Measures a run's auto metrics and configured ones, and checks the configured ones' gates; bools default to equals: true."""

    def __init__(self, base_dir: Path, registry: MetricRegistry | None = None):
        self.base_dir = base_dir
        self.registry = registry or MetricRegistry()

    def score(
        self, configs: list[MetricConfig], context: MetricContext
    ) -> tuple[dict[str, MetricResult], dict[str, GateResult]]:
        results = {metric.NAME: self._measure(metric(), context) for metric in AUTO_METRICS}
        gates = {}
        for config in configs:
            try:
                metric = self.registry.build(config, self.base_dir)
            except MetricError as e:
                results[config.name] = MetricResult(value=None, details={"error": str(e)})
                if config.gate is not None:
                    gates[config.name] = GateResult(passed=False, required=config.required)
                continue
            results[config.name] = self._measure(metric, context)
            gate = config.gate or (BOOL_GATE if metric.VALUE_TYPE == "bool" else None)
            if gate is not None:
                gates[config.name] = GateResult(
                    passed=gate.passes(results[config.name].value), required=config.required
                )
        return results, gates

    @staticmethod
    def _measure(metric: BaseMetric, context: MetricContext) -> MetricResult:
        try:
            return metric.measure(context)
        except Exception as e:
            logger.warning("Metric %s failed on case %s", metric.name, context.case.id, exc_info=True)
            return MetricResult(value=None, details={"error": f"{type(e).__name__}: {e}"})
