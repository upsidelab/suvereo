from typing import Literal

from pydantic import BaseModel

from agent.evaluation.aggregation import PASS_RATE

from .exit_code import ExitCode
from .suite_report import SuiteReport

SuiteRunStatus = Literal["complete", "partial"]


class SuiteVerdict(BaseModel):
    """How a suite run ended: complete, or partial when the budget stopped it before every planned run; its exit code;
    and the candidates whose pass rate is below the suite's pass_threshold."""

    status: SuiteRunStatus
    exit_code: ExitCode
    below_threshold: list[str]

    @classmethod
    def of(cls, report: SuiteReport) -> "SuiteVerdict":
        result, threshold = report.result, report.loaded.suite.pass_threshold
        below = [c.candidate for c in report.candidates if (c.metrics[PASS_RATE].value or 0.0) < threshold]
        partial = len(result.runs) < result.planned_runs
        if partial and result.stopped_reason is not None:
            exit_code = ExitCode.BUDGET_EXCEEDED
        elif below:
            exit_code = ExitCode.BELOW_PASS_THRESHOLD
        else:
            exit_code = ExitCode.PASSED
        return cls(status="partial" if partial else "complete", exit_code=exit_code, below_threshold=below)
