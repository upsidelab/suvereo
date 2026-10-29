from pathlib import Path
from typing import Any, Literal, NamedTuple

from enthusiast_common.evaluation.suite import SuiteKind

from agent.evaluation.resolved_kind import resolved_kind
from agent.evaluation.runner import RunResult

from .base_report_writer import BaseReportWriter
from .csv_table import CsvTable
from .judge_reasoning import REASONING, JudgeReasoning
from .suite_report import SuiteReport

OUTCOME_COLUMNS = {
    SuiteKind.EXECUTION: ["execution_succeeded", "failure_code", "attempts", "first_attempt_success"],
    SuiteKind.CONVERSATION: ["conversation_completed", "conversation_end", "goal_reached", "turns"],
}
PERFORMANCE_COLUMNS = [
    "duration_s",
    "cost_usd",
    "judge_cost_usd",
    "input_tokens",
    "output_tokens",
    "llm_calls",
    "tool_calls",
]
#: What simulated users cost, only in conversation suites.
USER_COST_COLUMN = "user_cost_usd"


class ResultsCsvWriter(BaseReportWriter):
    """results.csv: one row per run with its identity, outcome, cost and timing, every metric (with whether the run
    met its pass threshold, its components and a judge's reasoning), the missed thresholds and the trace file."""

    NAME = "results"

    def write(self, report: SuiteReport, run_dir: Path) -> list[Path]:
        metric_columns = self._metric_columns(report)
        kind = resolved_kind(report.loaded.suite)
        outcome_columns = OUTCOME_COLUMNS[kind]
        performance_columns = [*PERFORMANCE_COLUMNS, *([USER_COST_COLUMN] if kind == SuiteKind.CONVERSATION else [])]
        header = [
            *["run_id", "case_id", "tags", "candidate", "provider", "model", "variant", "repeat"],
            *["passed", "error", *outcome_columns, *performance_columns],
            *(column.header for column in metric_columns),
            *["failed_thresholds", "trace_file"],
        ]
        tags = {case.id: case.tags for case in report.cases}
        rows = [
            [
                *[report.run_id(run), run.case_id, tags.get(run.case_id, []), run.candidate],
                *[report.provider_of(run.model), run.model, run.variant, run.repeat],
                *[
                    run.passed,
                    run.trace.error,
                    *(self._metric_value(run, name) for name in [*outcome_columns, *performance_columns]),
                ],
                *(column.cell(run) for column in metric_columns),
                *[
                    [name for name, threshold in run.thresholds.items() if not threshold.passed],
                    report.linked_trace_path(run),
                ],
            ]
            for run in report.runs
        ]
        return [CsvTable.write(run_dir / "results.csv", header, rows)]

    @staticmethod
    def _metric_columns(report: SuiteReport) -> list["MetricColumn"]:
        """Per configured metric, in suite order: its value, whether the run met its pass threshold if any run was checked, each
        component any run reported, and the judge's reasoning if any run gave one."""
        columns = []
        for name in report.metric_configs:
            columns.append(MetricColumn(name, name, kind="value"))
            if any(name in run.thresholds for run in report.runs):
                columns.append(MetricColumn(f"{name}__passed", name, kind="threshold_passed"))
            reported = (c for run in report.runs if name in run.metrics for c in run.metrics[name].components)
            columns += [
                MetricColumn(f"{name}.{c}", name, kind="component", component=c) for c in dict.fromkeys(reported)
            ]
            if any(name in run.metrics and JudgeReasoning.by_criterion(run.metrics[name]) for run in report.runs):
                columns.append(MetricColumn(f"{name}.{REASONING}", name, kind=REASONING))
        return columns

    @staticmethod
    def _metric_value(run: RunResult, name: str) -> Any:
        result = run.metrics.get(name)
        return result.value if result else None


class MetricColumn(NamedTuple):
    """One metric column of results.csv: its header, the metric it reads, and what of it (value, threshold, component,
    reasoning)."""

    header: str
    metric: str
    kind: Literal["value", "threshold_passed", "component", "reasoning"]
    component: str | None = None

    def cell(self, run: RunResult) -> Any:
        if self.kind == "threshold_passed":
            threshold = run.thresholds.get(self.metric)
            return threshold.passed if threshold else None
        result = run.metrics.get(self.metric)
        if result is None:
            return None
        if self.kind == REASONING:
            return " | ".join(JudgeReasoning.lines(result)) or None
        if self.kind != "component":
            return result.value
        score = result.components.get(self.component)
        return JudgeReasoning.outcome(score) if result.binary_components and score is not None else score
