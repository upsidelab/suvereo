from pydantic import BaseModel, Field


class SuiteRunOptions(BaseModel):
    """How to run a suite, beyond what suite.yaml says."""

    parallel: int = Field(default=1, ge=1, description="Runs in flight at once.")
    budget_usd: float | None = Field(default=None, gt=0, description="Overrides the suite's budget_usd.")
    allow_real_integrations: bool = Field(
        default=False, description="Lets an existing agent use unmocked integrations."
    )
    keep_run_data: bool = Field(
        default=False, description="Keeps what the runs created for inspection: conversations, and a sandbox's DataSet."
    )
