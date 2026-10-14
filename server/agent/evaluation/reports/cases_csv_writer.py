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
        rows = []
        for case in report.cases:
            for candidate in report.candidates:
                runs = [run for run in candidate.runs if run.case_id == case.id]
                if runs:
                    passed = sum(run.passed for run in runs)
                    status = "pass" if passed == len(runs) else "fail" if passed == 0 else "flaky"
                    rows.append([case.id, case.tags, case.description, candidate.candidate, status, passed, len(runs)])
        return [CsvTable.write(run_dir / "cases.csv", header, rows)]
