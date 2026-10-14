from enthusiast_common.evaluation.loaded_suite import LoadedSuite
from enthusiast_common.evaluation.metrics import MetricRegistry
from enthusiast_common.evaluation.metrics.auto import AUTO_METRICS, Attempts
from enthusiast_common.evaluation.suite import Aggregate

from agent.evaluation.runner import RunResult
from agent.evaluation.runner.case_runner import JUDGE_COST

from .candidate_metrics import CandidateMetrics
from .metric_aggregate import MetricAggregate

PASS_RATE = "pass_rate"
FIRST_ATTEMPT_PASS_RATE = "first_attempt_pass_rate"
FLAKY_RATE = "flaky_rate"
DERIVED_METRICS = (PASS_RATE, FIRST_ATTEMPT_PASS_RATE, FLAKY_RATE)
TAG_PREFIX = "tag:"


class MetricAggregator:
    """Aggregates runs per candidate: every metric and component, the pass, first-attempt and flaky rates, and all of
    them again per case tag."""

    def __init__(
        self,
        value_types: dict[str, str],
        aggregates: dict[str, Aggregate] | None = None,
        case_tags: dict[str, list[str]] | None = None,
    ):
        self.value_types = value_types
        self.aggregates = aggregates or {}
        self.case_tags = case_tags or {}

    @classmethod
    def for_suite(cls, loaded: LoadedSuite) -> "MetricAggregator":
        """An aggregator knowing the value type and declared aggregate of every metric the suite measures.

        SuiteLoader makes a case's override keep its suite metric's type and aggregate, so the first config of a name
        speaks for every case.
        """
        value_types = {metric.NAME: metric.VALUE_TYPE for metric in AUTO_METRICS} | {JUDGE_COST: "number"}
        aggregates: dict[str, Aggregate] = {}
        registry = MetricRegistry()
        configs = [*loaded.suite.metrics, *(c for case in loaded.cases for c in loaded.suite.metrics_for(case))]
        for config in configs:
            if config.name in value_types:
                continue
            value_types[config.name] = registry.metric_class(config.type).VALUE_TYPE
            if config.aggregate:
                aggregates[config.name] = config.aggregate
        return cls(value_types, aggregates, {case.id: case.tags for case in loaded.cases})

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

    def aggregate_runs(self, runs: list[RunResult], by_tag: bool = True) -> dict[str, MetricAggregate]:
        """Every metric over the runs, plus the derived rates and, with by_tag, each again as tag:<tag>.<metric>."""
        summary = self._aggregate_measured_metrics(runs) | self._pass_and_flaky_rates(runs)
        if by_tag:
            tags = sorted({tag for run in runs for tag in self.case_tags.get(run.case_id, [])})
            for tag in tags:
                tagged = [run for run in runs if tag in self.case_tags.get(run.case_id, [])]
                per_tag = self._aggregate_measured_metrics(tagged) | self._pass_and_flaky_rates(tagged)
                summary |= {f"{TAG_PREFIX}{tag}.{name}": value for name, value in per_tag.items()}
        return summary

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
    def _pass_and_flaky_rates(runs: list[RunResult]) -> dict[str, MetricAggregate]:
        outcomes: dict[str, list[bool]] = {}
        for run in runs:
            outcomes.setdefault(run.case_id, []).append(run.passed)
        first_attempt = [run.passed and (run.metrics[Attempts.NAME].value or 0) <= 1 for run in runs]
        return {
            PASS_RATE: MetricAggregate.from_values([run.passed for run in runs], "bool"),
            FIRST_ATTEMPT_PASS_RATE: MetricAggregate.from_values(first_attempt, "bool"),
            FLAKY_RATE: MetricAggregate.from_values([len(set(passed)) > 1 for passed in outcomes.values()], "bool"),
        }
