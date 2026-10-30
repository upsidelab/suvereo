from typing import Any

from pydantic import BaseModel

from agent.evaluation.aggregation import PASS_RATE, CandidateMetrics

from .case_outcome import CaseOutcome, CaseStatus
from .summary_file import SummarizedCandidate, SummaryFile

STATUS_RANK: dict[str, int] = {"fail": 0, "flaky": 1, "pass": 2}


class ValueChange(BaseModel):
    """A figure in the baseline and now; delta when both are numbers."""

    before: Any = None
    after: Any = None
    delta: float | None = None

    @classmethod
    def between(cls, before: Any, after: Any) -> "ValueChange":
        numbers = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (before, after))
        return cls(before=before, after=after, delta=after - before if numbers else None)


class CandidateChange(BaseModel):
    """How one candidate's pass rate and metrics moved; before is None for a candidate the baseline didn't run."""

    candidate: str
    pass_rate: ValueChange
    metrics: dict[str, ValueChange]


class CaseChange(BaseModel):
    """A case whose status for a candidate changed between the baseline and now."""

    case_id: str
    candidate: str
    before: CaseStatus
    after: CaseStatus


class BaselineDiff(BaseModel):
    """This run against an earlier one (--baseline): each candidate's pass rate and metric changes, and the cases that
    regressed (e.g. pass to flaky) or improved, per candidate both runs share."""

    baseline: str
    baseline_started_at: str | None
    candidates: list[CandidateChange]
    regressed: list[CaseChange]
    improved: list[CaseChange]

    @classmethod
    def between(
        cls, candidates: list[CandidateMetrics], outcomes: list[CaseOutcome], metrics: list[str], baseline: SummaryFile
    ) -> "BaselineDiff":
        before_candidates = {c.candidate: c for c in baseline.candidates}
        before_statuses = {(c.case_id, c.candidate): c.status for c in baseline.cases}
        changes = [cls._candidate_change(c, before_candidates.get(c.candidate), metrics) for c in candidates]
        case_changes = [
            CaseChange(case_id=o.case_id, candidate=o.candidate, before=before, after=o.status)
            for o in outcomes
            if (before := before_statuses.get((o.case_id, o.candidate))) and before != o.status
        ]
        return cls(
            baseline=str(baseline.path),
            baseline_started_at=baseline.run.started_at,
            candidates=changes,
            regressed=[c for c in case_changes if STATUS_RANK[c.after] < STATUS_RANK[c.before]],
            improved=[c for c in case_changes if STATUS_RANK[c.after] > STATUS_RANK[c.before]],
        )

    @staticmethod
    def _candidate_change(
        candidate: CandidateMetrics, before: SummarizedCandidate | None, metrics: list[str]
    ) -> CandidateChange:
        before = before or SummarizedCandidate(candidate=candidate.candidate)
        before_metrics = before.metrics
        return CandidateChange(
            candidate=candidate.candidate,
            pass_rate=ValueChange.between(before.pass_rate, candidate.metrics[PASS_RATE].value),
            metrics={
                name: ValueChange.between(before_metrics.get(name), candidate.metrics[name].value)
                for name in metrics
                if name in candidate.metrics
            },
        )
