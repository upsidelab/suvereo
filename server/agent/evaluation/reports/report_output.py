from pathlib import Path

from enthusiast_common.evaluation.suite import ReportName

from .base_report_writer import BaseReportWriter
from .cases_csv_writer import CasesCsvWriter
from .comparison_csv_writer import ComparisonCsvWriter
from .metrics_csv_writer import MetricsCsvWriter
from .results_csv_writer import ResultsCsvWriter
from .suite_report import SuiteReport
from .trace_files_writer import TraceFilesWriter

WRITERS: list[type[BaseReportWriter]] = [
    ResultsCsvWriter,
    ComparisonCsvWriter,
    CasesCsvWriter,
    MetricsCsvWriter,
    TraceFilesWriter,
]


class ReportOutput:
    """Writes the reports a run selected (suite.yaml `reports:`, or the CLI's --reports) into its run directory."""

    def __init__(self, writers: list[type[BaseReportWriter]] | None = None):
        self.writers = {writer.NAME: writer for writer in (WRITERS if writers is None else writers)}

    def write(self, report: SuiteReport, names: list[ReportName], run_dir: Path) -> list[Path]:
        """Write each selected report that has a writer, in the order selected, and return the files written."""
        written: list[Path] = []
        for name in dict.fromkeys(names):
            if writer := self.writers.get(name):
                written += writer().write(report, run_dir)
        return written
