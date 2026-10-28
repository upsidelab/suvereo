from pathlib import Path

from suvereo_common.evaluation.suite import ReportName

from .base_report_writer import BaseReportWriter
from .cases_csv_writer import CasesCsvWriter
from .comparison_csv_writer import ComparisonCsvWriter
from .metrics_csv_writer import MetricsCsvWriter
from .report_md_writer import ReportMdWriter
from .results_csv_writer import ResultsCsvWriter
from .suite_report import SuiteReport
from .summary_json_writer import SummaryJsonWriter
from .trace_files_writer import TraceFilesWriter
from .transcripts_writer import TranscriptsWriter

WRITERS: list[type[BaseReportWriter]] = [
    ReportMdWriter,
    ResultsCsvWriter,
    ComparisonCsvWriter,
    CasesCsvWriter,
    MetricsCsvWriter,
    TraceFilesWriter,
    TranscriptsWriter,
]


class ReportOutput:
    """Writes summary.json and the reports a run selected (suite.yaml `reports:`, or the CLI's --reports) into its run
    directory."""

    def __init__(self, writers: list[type[BaseReportWriter]] | None = None):
        self.writers = {writer.NAME: writer for writer in (WRITERS if writers is None else writers)}

    def write(self, report: SuiteReport, names: list[ReportName], run_dir: Path) -> list[Path]:
        """Write summary.json, then each selected report in the order selected; return the files written."""
        written = SummaryJsonWriter().write(report, run_dir)
        for name in dict.fromkeys(names):
            if writer := self.writers.get(name):
                written += writer().write(report, run_dir)
        return written
