from pydantic import BaseModel, Field

from .run_result import RunResult


class SuiteRunResult(BaseModel):
    """Every run of a suite; partial when the budget ran out, or could not be tracked, before all planned runs started."""

    suite: str
    planned_runs: int
    runs: list[RunResult]
    spent_usd: float
    budget_exceeded: bool = False
    unpriced_models: list[str] = Field(default=[], description="Models whose cost spent_usd leaves out.")
