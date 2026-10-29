from typing import Any

from pydantic import BaseModel


class LLMCall(BaseModel):
    """One finished or failed LLM call, nested calls inside tools included."""

    run_id: str
    #: The tool, chain or agent run that made this call.
    parent_run_id: str | None = None
    #: The name asked for, which pricing is keyed on; ``model`` is often a dated snapshot of it.
    requested_model: str | None = None
    model: str | None = None
    #: Includes ``cached_input_tokens`` and both cache-write counts.
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_5m_input_tokens: int = 0
    cache_write_1h_input_tokens: int = 0
    #: Includes ``reasoning_tokens``.
    output_tokens: int = 0
    reasoning_tokens: int = 0
    duration_s: float | None = None
    finish_reason: str | None = None
    requested_tool_calls: list[dict[str, Any]] = []
    error: str | None = None
    usage_reported: bool = True
