from pathlib import Path

from .base_report_writer import BaseReportWriter
from .csv_table import CsvTable
from .suite_report import SuiteReport
from .threshold_text import threshold_text


class MetricsCsvWriter(BaseReportWriter):
    """metrics.csv, long format for pivots and charts: one row per run and metric, plus one per component, with
    whether the run met the metric's pass threshold and the threshold itself (e.g. "min 0.95")."""

    NAME = "metrics"

    def write(self, report: SuiteReport, run_dir: Path) -> list[Path]:
        header = [
            *["run_id", "case_id", "candidate", "repeat"],
            *["metric", "component", "value", "passed", "pass_threshold"],
        ]
        rows = []
        for run in report.runs:
            identity = [report.run_id(run), run.case_id, run.candidate, run.repeat]
            for name, result in run.metrics.items():
                threshold_result = run.thresholds.get(name)
                threshold = report.threshold_for(run.case_id, name) if threshold_result else None
                passed = threshold_result.passed if threshold_result else None
                rows.append([*identity, name, None, result.value, passed, threshold_text(threshold)])
                rows += [
                    [*identity, name, component, value, None, None] for component, value in result.components.items()
                ]
        return [CsvTable.write(run_dir / "metrics.csv", header, rows)]
