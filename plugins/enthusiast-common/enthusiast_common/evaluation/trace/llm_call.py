from typing import Any

from pydantic import BaseModel


class LLMCall(BaseModel):
    """One finished or failed LLM call, nested calls inside tools included."""

    run_id: str
    #: The run that made the call directly: a tool, a chain or the agent. ExecutionTrace.llm_calls_within follows
    #: these links up through chains, so a call inside a chain inside a tool still counts as within the tool.
    parent_run_id: str | None = None
    #: The name asked for, which pricing is keyed on; ``model`` is often a dated snapshot of it.
    requested_model: str | None = None
    model: str | None = None
    #: Includes ``cached_input_tokens`` and ``cache_write_input_tokens``.
    input_tokens: int = 0
    cached_input_tokens: int = 0
    #: Input tokens written to the provider's prompt cache, billed above the input rate (e.g. Anthropic).
    cache_write_input_tokens: int = 0
    #: Includes ``reasoning_tokens``.
    output_tokens: int = 0
    reasoning_tokens: int = 0
    duration_s: float | None = None
    finish_reason: str | None = None
    requested_tool_calls: list[dict[str, Any]] = []
    error: str | None = None
    #: False when the provider sent no token counts (e.g. streaming without usage); the call then can't be priced.
    usage_reported: bool = True
