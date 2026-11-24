from pathlib import Path

from suvereo_common.evaluation.suite import ReportName

from agent.evaluation.reports.base_report_writer import BaseReportWriter
from agent.evaluation.reports.cases_csv_writer import CasesCsvWriter
from agent.evaluation.reports.comparison_csv_writer import ComparisonCsvWriter
from agent.evaluation.reports.metrics_csv_writer import MetricsCsvWriter
from agent.evaluation.reports.report_md_writer import ReportMdWriter
from agent.evaluation.reports.results_csv_writer import ResultsCsvWriter
from agent.evaluation.reports.suite_report import SuiteReport
from agent.evaluation.reports.summary_json_writer import SummaryJsonWriter
from agent.evaluation.reports.trace_files_writer import TraceFilesWriter
from agent.evaluation.reports.transcripts_writer import TranscriptsWriter

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
