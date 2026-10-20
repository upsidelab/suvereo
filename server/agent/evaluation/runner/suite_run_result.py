from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .run_result import RunResult

StopReason = Literal["budget_spent", "budget_untracked"]


class SuiteRunResult(BaseModel):
    """Every run of a suite; partial when stopped before all planned runs started (see stopped_reason)."""

    suite: str
    planned_runs: int
    runs: list[RunResult]
    spent_usd: float = Field(description="USD of every priced call; calls of unpriced_models are not in it.")
    stopped_reason: StopReason | None = Field(
        default=None,
        description="budget_spent: the budget ran out; budget_untracked: a call could not be priced, so it could not be "
        "tracked.",
    )
    unpriced_models: list[str] = Field(default=[], description="Models with calls spent_usd could not price.")
    budget_usd: float | None = None
    pricing_as_of: str = Field(default="", description="The date of the prices spent_usd is worked out with.")
    started_at: datetime | None = None
    finished_at: datetime | None = None
