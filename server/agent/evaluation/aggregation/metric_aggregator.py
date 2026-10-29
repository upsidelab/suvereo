from enthusiast_common.evaluation.loaded_suite import LoadedSuite
from enthusiast_common.evaluation.metrics import MetricRegistry
from enthusiast_common.evaluation.metrics.auto import AUTO_METRICS, Attempts
from enthusiast_common.evaluation.suite import Aggregate, SuiteKind

from agent.evaluation.resolved_kind import resolved_kind
from agent.evaluation.runner import RunResult
from agent.evaluation.runner.case_runner import JUDGE_COST, USER_COST
from agent.evaluation.suite_metric_configs import suite_metric_configs

from .candidate_metrics import CandidateMetrics
from .metric_aggregate import MetricAggregate

PASS_RATE = "pass_rate"
FIRST_ATTEMPT_PASS_RATE = "first_attempt_pass_rate"
FLAKY_RATE = "flaky_rate"
DERIVED_METRICS = (PASS_RATE, FIRST_ATTEMPT_PASS_RATE, FLAKY_RATE)
#: The rates a suite of each kind reports; conversations have no attempts, so no first-attempt rate.
RATES: dict[SuiteKind, tuple[str, ...]] = {
    SuiteKind.EXECUTION: DERIVED_METRICS,
    SuiteKind.CONVERSATION: (PASS_RATE, FLAKY_RATE),
}


class MetricAggregator:
    """Aggregates runs per candidate: every metric and component, and the rates of the suite's kind (RATES)."""

    def __init__(
        self,
        value_types: dict[str, str],
        aggregates: dict[str, Aggregate] | None = None,
        kind: SuiteKind = SuiteKind.EXECUTION,
    ):
        self.value_types = value_types
        self.aggregates = aggregates or {}
        self.kind = kind

    @classmethod
    def for_suite(cls, loaded: LoadedSuite) -> "MetricAggregator":
        """An aggregator knowing the value type and declared aggregate of every metric the suite measures."""
        value_types = {metric.NAME: metric.VALUE_TYPE for metric in AUTO_METRICS} | {
            JUDGE_COST: "number",
            USER_COST: "number",
        }
        aggregates: dict[str, Aggregate] = {}
        registry = MetricRegistry()
        for config in suite_metric_configs(loaded).values():
            value_types[config.name] = registry.metric_class(config.type).VALUE_TYPE
            if config.aggregate:
                aggregates[config.name] = config.aggregate
        return cls(value_types, aggregates, resolved_kind(loaded.suite))

    def aggregate_per_candidate(self, runs: list[RunResult]) -> list[CandidateMetrics]:
        """One entry per candidate, in the order their first run appears."""
        grouped: dict[str, list[RunResult]] = {}
        for run in runs:
            grouped.setdefault(run.candidate, []).append(run)
        return [
            CandidateMetrics(
                candidate=name,
                model=group[0].model,
                variant=group[0].variant,
                runs=group,
                metrics=self.aggregate_runs(group),
            )
            for name, group in grouped.items()
        ]

    def aggregate_runs(self, runs: list[RunResult]) -> dict[str, MetricAggregate]:
        """Every metric over the runs, plus the rates of the suite's kind."""
        rates = self._rates(runs)
        return self._aggregate_measured_metrics(runs) | {name: rates[name] for name in RATES[self.kind]}

    def _aggregate_measured_metrics(self, runs: list[RunResult]) -> dict[str, MetricAggregate]:
        names = list(dict.fromkeys(name for run in runs for name in run.metrics))
        summary = {}
        for name in names:
            results = [run.metrics.get(name) for run in runs]
            value_type = self.value_types.get(name, "number")
            summary[name] = MetricAggregate.from_values(
                [r.value if r else None for r in results], value_type, self.aggregates.get(name)
            )
            components = list(dict.fromkeys(c for r in results if r for c in r.components))
            for component in components:
                values = [r.components.get(component) if r else None for r in results]
                summary[f"{name}.{component}"] = MetricAggregate.from_values(values, "number")
        return summary

    @staticmethod
    def _rates(runs: list[RunResult]) -> dict[str, MetricAggregate]:
        outcomes: dict[str, list[bool]] = {}
        for run in runs:
            outcomes.setdefault(run.case_id, []).append(run.passed)
        attempts = [run.metrics.get(Attempts.NAME) for run in runs]
        first_attempt = [
            None if result is None else run.passed and (result.value or 0) <= 1 for run, result in zip(runs, attempts)
        ]
        return {
            PASS_RATE: MetricAggregate.from_values([run.passed for run in runs], "bool"),
            FIRST_ATTEMPT_PASS_RATE: MetricAggregate.from_values(first_attempt, "bool"),
            FLAKY_RATE: MetricAggregate.from_values([len(set(passed)) > 1 for passed in outcomes.values()], "bool"),
        }
