from pathlib import Path
from typing import Any, Literal, NamedTuple

from agent.evaluation.runner import RunResult

from .base_report_writer import BaseReportWriter
from .csv_table import CsvTable
from .suite_report import SuiteReport

OUTCOME_COLUMNS = ["execution_succeeded", "failure_code", "attempts", "first_attempt_success"]
PERFORMANCE_COLUMNS = [
    "duration_s",
    "cost_usd",
    "judge_cost_usd",
    "input_tokens",
    "output_tokens",
    "llm_calls",
    "tool_calls",
]


class ResultsCsvWriter(BaseReportWriter):
    """results.csv: one row per run with its identity, outcome, cost and timing, every metric (with whether its gate
    passed, and its components), the failed gates and the trace file."""

    NAME = "results"

    def write(self, report: SuiteReport, run_dir: Path) -> list[Path]:
        metric_columns = self._metric_columns(report)
        header = [
            *["run_id", "case_id", "tags", "candidate", "provider", "model", "variant", "repeat"],
            *["passed", "error", *OUTCOME_COLUMNS, *PERFORMANCE_COLUMNS],
            *(column.header for column in metric_columns),
            *["failed_gates", "trace_file"],
        ]
        tags = {case.id: case.tags for case in report.cases}
        rows = [
            [
                *[report.run_id(run), run.case_id, tags.get(run.case_id, []), run.candidate],
                *[report.provider_of(run.model), run.model, run.variant, run.repeat],
                *[
                    run.passed,
                    run.trace.error,
                    *(self._metric_value(run, name) for name in [*OUTCOME_COLUMNS, *PERFORMANCE_COLUMNS]),
                ],
                *(column.cell(run) for column in metric_columns),
                *[[name for name, gate in run.gates.items() if not gate.passed], report.linked_trace_path(run)],
            ]
            for run in report.runs
        ]
        return [CsvTable.write(run_dir / "results.csv", header, rows)]

    @staticmethod
    def _metric_columns(report: SuiteReport) -> list["MetricColumn"]:
        """Per configured metric, in suite order: its value, whether its gate passed if any run gated it, and each
        component any run reported."""
        columns = []
        for name in report.metric_configs:
            columns.append(MetricColumn(name, name, kind="value"))
            if any(name in run.gates for run in report.runs):
                columns.append(MetricColumn(f"{name}__passed", name, kind="gate_passed"))
            reported = (c for run in report.runs if name in run.metrics for c in run.metrics[name].components)
            columns += [
                MetricColumn(f"{name}.{c}", name, kind="component", component=c) for c in dict.fromkeys(reported)
            ]
        return columns

    @staticmethod
    def _metric_value(run: RunResult, name: str) -> Any:
        result = run.metrics.get(name)
        return result.value if result else None


class MetricColumn(NamedTuple):
    """One metric column of results.csv: its header, the metric it reads, and what of it (value, gate, component)."""

    header: str
    metric: str
    kind: Literal["value", "gate_passed", "component"]
    component: str | None = None

    def cell(self, run: RunResult) -> Any:
        if self.kind == "gate_passed":
            gate = run.gates.get(self.metric)
            return gate.passed if gate else None
        result = run.metrics.get(self.metric)
        if result is None:
            return None
        return result.components.get(self.component) if self.kind == "component" else result.value
