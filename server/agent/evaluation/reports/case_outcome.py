from typing import Literal

from pydantic import BaseModel

CaseStatus = Literal["pass", "fail", "flaky"]


class CaseOutcome(BaseModel):
    case_id: str
    candidate: str
    passed_runs: int
    runs: int

    @property
    def status(self) -> CaseStatus:
        if self.passed_runs == self.runs:
            return "pass"
        return "fail" if self.passed_runs == 0 else "flaky"
