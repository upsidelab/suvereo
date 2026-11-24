import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError
from suvereo_common.evaluation.errors import EvalSuiteError

from agent.evaluation.reports.case_outcome import CaseStatus
from agent.evaluation.reports.run_directory import LATEST_LINK, RESULTS_DIR

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
    path: Path
    run: SummarizedRun = SummarizedRun()
    candidates: list[SummarizedCandidate] = []
    cases: list[SummarizedCase] = []
    failing_runs: list[SummarizedFailingRun] = []

    @classmethod
    def load(cls, reference: str, suite_dir: Path) -> "SummaryFile":
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
        return list(dict.fromkeys(run.case_id for run in self.failing_runs))
