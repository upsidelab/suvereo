import json
from pathlib import Path
from typing import Any

from enthusiast_common.evaluation.errors import EvalSuiteError
from pydantic import BaseModel, ValidationError

from .case_outcome import CaseStatus
from .run_directory import LATEST_LINK, RESULTS_DIR

SUMMARY_FILE = "summary.json"


class SummarizedCandidate(BaseModel):
    candidate: str
    pass_rate: float | None = None
    metrics: dict[str, Any] = {}


class SummarizedCase(BaseModel):
    case_id: str
    candidate: str
    status: CaseStatus


class SummarizedFailingRun(BaseModel):
    case_id: str


class SummarizedRun(BaseModel):
    started_at: str | None = None


class SummaryFile(BaseModel):
    """The parts of an earlier run's summary.json read back to compare against (--baseline) or to rerun its failures;
    other keys are ignored, and summaries without cases give no case changes."""

    path: Path
    run: SummarizedRun = SummarizedRun()
    candidates: list[SummarizedCandidate] = []
    cases: list[SummarizedCase] = []
    failing_runs: list[SummarizedFailingRun] = []

    @classmethod
    def load(cls, reference: str, suite_dir: Path) -> "SummaryFile":
        """Read a summary by reference: 'latest' (the suite's newest run), a run directory, or a summary.json path;
        raises EvalSuiteError when it is missing, unreadable or not shaped like a summary."""
        path = suite_dir / RESULTS_DIR / LATEST_LINK if reference == LATEST_LINK else Path(reference)
        if path.is_dir():
            path = path / SUMMARY_FILE
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise EvalSuiteError(f"Cannot read the summary {path}: {e}") from e
        if not isinstance(content, dict):
            raise EvalSuiteError(f"{path} is not a summary.json.")
        try:
            return cls.model_validate({**content, "path": path.resolve()})
        except ValidationError as e:
            raise EvalSuiteError(f"{path} is not a summary.json: {e}") from e

    def failing_case_ids(self) -> list[str]:
        """The ids of the cases with a failed run, in the order they first failed."""
        return list(dict.fromkeys(run.case_id for run in self.failing_runs))
