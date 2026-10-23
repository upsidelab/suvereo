from pydantic import BaseModel


class Turn(BaseModel):
    """One user message in a conversation and the agent's answer to it, with the calls the agent made meanwhile."""

    user_message: str
    answer: str | None = None
    error: str | None = None
    duration_s: float | None = None
    llm_call_run_ids: list[str] = []
    tool_call_run_ids: list[str] = []
