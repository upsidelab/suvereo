from pydantic import BaseModel


class Attempt(BaseModel):
    """One pass of an execution's validator loop; number 1 is the first, higher ones are retries."""

    number: int
    response: str
    passed: bool
    validator_feedback: str | None = None
    failure_code: str | None = None
