import json
from collections import Counter
from typing import Any, Literal

from ...suite import AgenticExecutionEvalCase, ConversationEvalCase
from ..metric_context import MetricContext

Section = Literal["input", "outcome", "output", "expected", "trace_summary"]
MAX_SUMMARY_VALUE = 1000


class JudgeMaterial:
    """The parts of a run an LLM metric shows its judge, each under its own heading."""

    @classmethod
    def build_prompt_text(cls, context: MetricContext, sections: list[Section]) -> str:
        """Build the run details pasted into the judge's prompt: each chosen section under a '## <section>' heading.

        input is the case input and file names (for a conversation, the user messages sent and the simulated user's
        goal and persona), outcome states how the run ended and which mocked systems it called (so "nothing was
        ordered" is stated, not left to be noticed), output and expected are JSON, trace_summary lists the tool calls,
        mock calls and validator attempts.
        """
        renderers = {
            "output": lambda: cls._as_json(context.trace.output),
            "expected": lambda: cls._as_json(context.case.expected),
            "input": lambda: cls._as_json(cls._input(context)),
            "outcome": lambda: cls._outcome(context),
            "trace_summary": lambda: cls._trace_summary(context),
        }
        return "\n\n".join(f"## {section}\n{renderers[section]()}" for section in sections)

    @staticmethod
    def _as_json(value: Any) -> str:
        return json.dumps(value, indent=2, default=str, ensure_ascii=False)

    @staticmethod
    def _is_conversation(context: MetricContext) -> bool:
        return isinstance(context.case, ConversationEvalCase)

    @staticmethod
    def _input(context: MetricContext) -> dict[str, Any]:
        case, files = context.case, [f.name for f in context.case.files]
        if isinstance(case, ConversationEvalCase):
            material: dict[str, Any] = {"user_messages": [turn.user_message for turn in context.trace.turns]}
            if case.simulated_user is not None:
                user = case.simulated_user
                material["simulated_user"] = {"goal": user.goal, "persona": user.persona}
            return {**material, "files": files}
        execution_input = case.input if isinstance(case, AgenticExecutionEvalCase) else {}
        return {"input": execution_input, "files": files}

    @classmethod
    def _outcome(cls, context: MetricContext) -> str:
        trace = context.trace
        result = trace.execution_result
        if cls._is_conversation(context):
            ended = cls._conversation_outcome(context)
        elif trace.error or result is None:
            ended = f"crashed: {trace.error or 'no result'}"
        elif result.success:
            ended = "succeeded"
        else:
            ended = f"failed ({result.failure_code})" + (
                f": {result.failure_summary}" if result.failure_summary else ""
            )
        calls = Counter(call.method for call in trace.mock_calls)
        called = ", ".join(f"{method} ×{count}" for method, count in calls.items())
        return f"run: {ended}\nmock calls: {called or 'none; the agent called no mocked external system'}"

    @staticmethod
    def _conversation_outcome(context: MetricContext) -> str:
        trace = context.trace
        if trace.error:
            return f"crashed after {len(trace.turns)} turn(s): {trace.error}"
        if not trace.turns:
            return "ended before the first turn"
        return f"conversation of {len(trace.turns)} turn(s), every turn answered"

    @classmethod
    def _trace_summary(cls, context: MetricContext) -> str:
        trace = context.trace
        lines = [
            f"tool {c.name}({cls._truncated(c.args)}) -> {cls._truncated(c.error or c.output)}"
            for c in trace.tool_calls
        ]
        lines += [
            f"mock {c.method}({cls._truncated(c.arguments)}) -> {cls._truncated(c.error or c.result)}"
            for c in trace.mock_calls
        ]
        lines += [
            f"attempt {a.number}: {'passed' if a.passed else f'failed: {a.validator_feedback}'}" for a in trace.attempts
        ]
        return "\n".join(lines) or "(nothing happened)"

    @staticmethod
    def _truncated(value: Any) -> str:
        text = json.dumps(value, default=str, ensure_ascii=False) if not isinstance(value, str) else value
        return text if len(text) <= MAX_SUMMARY_VALUE else text[:MAX_SUMMARY_VALUE] + "…"
