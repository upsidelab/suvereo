import json
from pathlib import Path

from .base_report_writer import BaseReportWriter
from .suite_report import SuiteReport


class TraceFilesWriter(BaseReportWriter):
    """runs/<run_id>.json: each run's verdict, metric results (values, components, details such as a judge's
    reasoning) and thresholds, then its full trace (LLM and tool calls, mock calls, attempts, output), for debugging."""

    NAME = "traces"

    def write(self, report: SuiteReport, run_dir: Path) -> list[Path]:
        written = []
        for run in report.runs:
            path = run_dir / report.trace_path(run)
            path.parent.mkdir(parents=True, exist_ok=True)
            content = {
                "passed": run.passed,
                "metrics": {name: result.model_dump(mode="json") for name, result in run.metrics.items()},
                "thresholds": {name: threshold.model_dump(mode="json") for name, threshold in run.thresholds.items()},
                **run.trace.model_dump(mode="json"),
            }
            path.write_text(json.dumps(content, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
            written.append(path)
        return written
