from pathlib import Path
from typing import Any

from suvereo_common.evaluation.metrics.auto import CostUsd, DurationSeconds
from suvereo_common.evaluation.suite import SuiteKind

from agent.evaluation.aggregation import CandidateMetrics
from agent.evaluation.aggregation.metric_aggregate import DEFAULT_AGGREGATE_NAMES, MetricAggregate
from agent.evaluation.reports.base_report_writer import BaseReportWriter
from agent.evaluation.reports.csv_table import CsvTable
from agent.evaluation.reports.suite_report import SuiteReport
from agent.evaluation.runner.case_runner import JUDGE_COST, USER_COST

#: The comparison column totalling each cost apart from the agent's.
COST_TOTALS = {JUDGE_COST: "judge_cost_total_usd", USER_COST: "user_cost_total_usd"}


class ComparisonCsvWriter(BaseReportWriter):
    NAME = "comparison"

    def write(self, report: SuiteReport, run_dir: Path) -> list[Path]:
        metric_columns = {
            name: self._aggregate_column_name(name, config.aggregate, report)
            for name, config in report.metric_configs.items()
        }
        costs = [JUDGE_COST, *([USER_COST] if report.kind == SuiteKind.CONVERSATION else [])]
        header = [
            *["candidate", "provider", "model", "variant", "runs", *report.rates],
            *(self._aggregate_column_name(name, None, report) for name in report.outcome_figures),
            *metric_columns.values(),
            *["duration_p50_s", "duration_p95_s", "cost_mean_usd", "cost_total_usd"],
            *(COST_TOTALS[cost] for cost in costs),
        ]
        rows = [
            [
                *[candidate.candidate, report.provider_of(candidate.model), candidate.model, candidate.variant],
                *[
                    len(candidate.runs),
                    *(self._metric_value(candidate, name) for name in [*report.rates, *report.outcome_figures]),
                ],
                *(self._aggregate_value(candidate, name, report) for name in metric_columns),
                *[
                    self._aggregate_figure(candidate, DurationSeconds.NAME, "p50"),
                    self._aggregate_figure(candidate, DurationSeconds.NAME, "p95"),
                ],
                *[
                    self._aggregate_figure(candidate, CostUsd.NAME, "mean"),
                    self._aggregate_figure(candidate, CostUsd.NAME, "sum"),
                ],
                *(self._aggregate_figure(candidate, cost, "sum") for cost in costs),
            ]
            for candidate in report.candidates
        ]
        return [CsvTable.write(run_dir / "comparison.csv", header, rows)]

    @staticmethod
    def _aggregate_column_name(name: str, aggregate: str | None, report: SuiteReport) -> str:
        value_type = next((c.metrics[name].value_type for c in report.candidates if name in c.metrics), "number")
        return f"{name}__{aggregate or DEFAULT_AGGREGATE_NAMES[value_type]}"

    @staticmethod
    def _aggregate_value(candidate: CandidateMetrics, name: str, report: SuiteReport) -> Any:
        figures = candidate.metrics.get(name)
        if figures is None:
            return None
        if report.metric_configs[name].aggregate == "distribution":
            return [f"{label}:{count}" for label, count in figures.distribution.items()]
        return figures.value

    @staticmethod
    def _metric_value(candidate: CandidateMetrics, name: str) -> Any:
        figures = candidate.metrics.get(name)
        return figures.value if figures else None

    @staticmethod
    def _aggregate_figure(candidate: CandidateMetrics, name: str, figure: str) -> float | None:
        figures: MetricAggregate | None = candidate.metrics.get(name)
        return getattr(figures, figure) if figures else None
