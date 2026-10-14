import time
from typing import Any
from uuid import UUID

from enthusiast_common.evaluation.trace import LLMCall, ToolCall, TraceRecorder
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from agent.evaluation.run_context import EvalRunContext


class TraceCallbackHandler(BaseCallbackHandler):
    """Records LLM and tool calls into the current run's trace (or a given recorder); a no-op outside an evaluation."""

    def __init__(self, recorder: TraceRecorder | None = None):
        self._recorder = recorder
        self._llm_starts: dict[UUID, tuple[float, str | None]] = {}
        self._tool_starts: dict[UUID, tuple[float, str, dict[str, Any]]] = {}

    def on_chain_start(
        self, serialized, inputs, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        self._record_parent(run_id, parent_run_id)

    def on_retriever_start(
        self, serialized, query, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        self._record_parent(run_id, parent_run_id)

    def on_chat_model_start(
        self, serialized, messages, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        self._record_parent(run_id, parent_run_id)
        self._start_llm(run_id, kwargs)

    def on_llm_start(
        self, serialized, prompts, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        self._record_parent(run_id, parent_run_id)
        self._start_llm(run_id, kwargs)

    def on_llm_end(
        self, response: LLMResult, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        started, requested_model = self._llm_starts.pop(run_id, (None, None))
        recorder = self._active_recorder()
        if recorder is None:
            return
        generation = response.generations[0][0] if response.generations and response.generations[0] else None
        message = getattr(generation, "message", None)
        usage = getattr(message, "usage_metadata", None)
        input_details = (usage or {}).get("input_token_details") or {}
        metadata = getattr(message, "response_metadata", None) or {}
        recorder.record_llm_call(
            LLMCall(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                requested_model=requested_model,
                model=metadata.get("model_name") or metadata.get("model") or requested_model,
                input_tokens=(usage or {}).get("input_tokens", 0),
                cached_input_tokens=input_details.get("cache_read", 0) or 0,
                cache_write_5m_input_tokens=(
                    input_details.get("ephemeral_5m_input_tokens") or input_details.get("cache_creation") or 0
                ),
                cache_write_1h_input_tokens=input_details.get("ephemeral_1h_input_tokens") or 0,
                output_tokens=(usage or {}).get("output_tokens", 0),
                reasoning_tokens=((usage or {}).get("output_token_details") or {}).get("reasoning", 0) or 0,
                usage_reported=usage is not None,
                duration_s=self._elapsed(started),
                finish_reason=metadata.get("finish_reason") or metadata.get("stop_reason"),
                requested_tool_calls=[
                    {"name": c["name"], "args": c["args"]} for c in (getattr(message, "tool_calls", None) or [])
                ],
            )
        )

    def on_llm_error(
        self, error: BaseException, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        started, requested_model = self._llm_starts.pop(run_id, (None, None))
        recorder = self._active_recorder()
        if recorder is None:
            return
        recorder.record_llm_call(
            LLMCall(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                requested_model=requested_model,
                model=requested_model,
                duration_s=self._elapsed(started),
                error=f"{type(error).__name__}: {error}",
            )
        )

    def on_tool_start(
        self,
        serialized: dict,
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        inputs: dict | None = None,
        **kwargs: Any,
    ) -> None:
        self._record_parent(run_id, parent_run_id)
        args = inputs if isinstance(inputs, dict) else {"input": input_str}
        self._tool_starts[run_id] = (time.perf_counter(), (serialized or {}).get("name", "unknown"), args)

    def on_tool_end(self, output: Any, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any) -> None:
        self._finish_tool(run_id, parent_run_id, output=str(getattr(output, "content", output)))

    def on_tool_error(
        self, error: BaseException, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        self._finish_tool(run_id, parent_run_id, error=f"{type(error).__name__}: {error}")

    def _record_parent(self, run_id: UUID, parent_run_id: UUID | None) -> None:
        """Remember which run started this one, so nested LLM calls can be traced back to their tool."""
        recorder = self._active_recorder()
        if recorder is not None and parent_run_id is not None:
            recorder.record_run_parent(str(run_id), str(parent_run_id))

    def _start_llm(self, run_id: UUID, kwargs: dict[str, Any]) -> None:
        params = kwargs.get("invocation_params") or {}
        self._llm_starts[run_id] = (time.perf_counter(), params.get("model_name") or params.get("model"))

    def _finish_tool(
        self, run_id: UUID, parent_run_id: UUID | None, output: str | None = None, error: str | None = None
    ) -> None:
        recorder = self._active_recorder()
        started, name, args = self._tool_starts.pop(run_id, (None, "unknown", {}))
        if recorder is None:
            return
        recorder.record_tool_call(
            ToolCall(
                run_id=str(run_id),
                parent_run_id=str(parent_run_id) if parent_run_id else None,
                name=name,
                args=args,
                output=output,
                error=error,
                duration_s=self._elapsed(started),
            )
        )

    def _active_recorder(self) -> TraceRecorder | None:
        if self._recorder is not None:
            return self._recorder
        context = EvalRunContext.current()
        return context.recorder if context else None

    @staticmethod
    def _elapsed(started: float | None) -> float | None:
        return None if started is None else time.perf_counter() - started
