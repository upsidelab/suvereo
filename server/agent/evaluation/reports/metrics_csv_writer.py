from pathlib import Path

from .base_report_writer import BaseReportWriter
from .csv_table import CsvTable
from .gate_text import gate_text
from .suite_report import SuiteReport


class MetricsCsvWriter(BaseReportWriter):
    """metrics.csv, long format for pivots and charts: one row per run and metric, plus one per component, with
    whether the metric's gate passed and the gate itself (e.g. "min 0.95")."""

    NAME = "metrics"

    def write(self, report: SuiteReport, run_dir: Path) -> list[Path]:
        header = ["run_id", "case_id", "candidate", "repeat", "metric", "component", "value", "passed", "gate"]
        rows = []
        for run in report.runs:
            identity = [report.run_id(run), run.case_id, run.candidate, run.repeat]
            for name, result in run.metrics.items():
                gate_result = run.gates.get(name)
                gate = report.gate_for(run.case_id, name) if gate_result else None
                passed = gate_result.passed if gate_result else None
                rows.append([*identity, name, None, result.value, passed, gate_text(gate)])
                rows += [
                    [*identity, name, component, value, None, None] for component, value in result.components.items()
                ]
        return [CsvTable.write(run_dir / "metrics.csv", header, rows)]
