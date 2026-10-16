from pathlib import Path

from enthusiast_common.evaluation.loaded_suite import LoadedSuite
from enthusiast_common.evaluation.suite import ReportName
from pydantic import BaseModel, ConfigDict

from agent.evaluation.reports import (
    GitState,
    ReportOutput,
    RunDirectory,
    RunHistory,
    SuiteReport,
    SuiteVerdict,
    SummaryFile,
)
from agent.evaluation.runner import SuiteRunner, SuiteRunOptions

RAW_RESULT_FILE = "run_result.json"


class ReportWritingError(Exception):
    """The suite ran but its reports could not be written; the raw results were saved instead."""


class SuiteEvaluationOutcome(BaseModel):
    """A finished evaluation: the report it wrote, its verdict, and the directory holding its files."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    report: SuiteReport
    verdict: SuiteVerdict
    run_dir: Path


class SuiteEvaluation:
    """One evaluation end to end: runs the suite, writes summary.json and the selected reports to a new run directory,
    and records the run in the suite's history."""

    def __init__(
        self,
        loaded: LoadedSuite,
        options: SuiteRunOptions | None = None,
        reports: list[ReportName] | None = None,
        baseline: SummaryFile | None = None,
        note: str = "",
        args: list[str] | None = None,
    ):
        self.loaded = loaded
        self.options = options or SuiteRunOptions()
        self.reports = loaded.suite.reports if reports is None else reports
        self.baseline = baseline
        self.note = note
        self.args = args or []

    def run(self) -> SuiteEvaluationOutcome:
        """Run the suite and write its outputs; raises ReportWritingError, after saving the raw results, when the
        reports cannot be made, so a paid-for run is never lost."""
        result = SuiteRunner(self.loaded, self.options).run()
        run_dir = RunDirectory.create(self.loaded.base_dir)
        try:
            report = SuiteReport(
                self.loaded,
                result,
                self.reports,
                git=GitState.of(self.loaded.base_dir),
                args=self.args,
                baseline=self.baseline,
            )
            ReportOutput().write(report, self.reports, run_dir)
            RunHistory(self.loaded.base_dir).record(report, run_dir, self.note)
        except Exception as e:
            raw = run_dir / RAW_RESULT_FILE
            raw.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            raise ReportWritingError(f"Writing the reports failed; the raw run results are in {raw}.") from e
        return SuiteEvaluationOutcome(report=report, verdict=SuiteVerdict.of(report), run_dir=run_dir)
