from pathlib import Path

from .base_report_writer import BaseReportWriter
from .suite_report import SuiteReport


class TraceFilesWriter(BaseReportWriter):
    """runs/<run_id>.json: each run's full trace (LLM and tool calls, mock calls, attempts, output), for debugging."""

    NAME = "traces"

    def write(self, report: SuiteReport, run_dir: Path) -> list[Path]:
        written = []
        for run in report.runs:
            path = run_dir / report.trace_path(run)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(run.trace.model_dump_json(indent=2), encoding="utf-8")
            written.append(path)
        return written
