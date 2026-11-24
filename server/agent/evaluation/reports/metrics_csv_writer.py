import json
from pathlib import Path

from agent.evaluation.reports.base_report_writer import BaseReportWriter
from agent.evaluation.reports.csv_table import CsvTable
from agent.evaluation.reports.suite_report import SuiteReport
from agent.evaluation.reports.threshold_text import threshold_text


class MetricsCsvWriter(BaseReportWriter):
    NAME = "metrics"

    def write(self, report: SuiteReport, run_dir: Path) -> list[Path]:
        header = [
            *["run_id", "case_id", "candidate", "repeat"],
            *["metric", "component", "value", "passed", "pass_threshold", "details"],
        ]
        rows = []
        for run in report.runs:
            identity = [report.run_id(run), run.case_id, run.candidate, run.repeat]
            for name, result in run.metrics.items():
                threshold_result = run.thresholds.get(name)
                threshold = report.threshold_for(run.case_id, name) if threshold_result else None
                passed = threshold_result.passed if threshold_result else None
                details = json.dumps(result.details, default=str, ensure_ascii=False) if result.details else None
                rows.append([*identity, name, None, result.value, passed, threshold_text(threshold), details])
                rows += [
                    [*identity, name, component, value, None, None, None]
                    for component, value in result.components.items()
                ]
        return [CsvTable.write(run_dir / "metrics.csv", header, rows)]
