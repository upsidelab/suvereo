from pathlib import Path

from .base_report_writer import BaseReportWriter
from .csv_table import CsvTable
from .suite_report import SuiteReport


class CasesCsvWriter(BaseReportWriter):
    """cases.csv: one row per case and candidate with how its repeats went: pass (all passed), fail (none did) or
    flaky, and how many passed; filter on status to find the cases a candidate fails."""

    NAME = "cases"

    def write(self, report: SuiteReport, run_dir: Path) -> list[Path]:
        header = ["case_id", "tags", "description", "candidate", "status", "passed_runs", "runs"]
        cases = {case.id: case for case in report.cases}
        rows = [
            [
                o.case_id,
                cases[o.case_id].tags,
                cases[o.case_id].description,
                o.candidate,
                o.status,
                o.passed_runs,
                o.runs,
            ]
            for o in report.case_outcomes()
        ]
        return [CsvTable.write(run_dir / "cases.csv", header, rows)]
