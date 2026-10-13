import json
from typing import Any, Literal

from ..metric_context import MetricContext

Section = Literal["output", "expected", "input_text", "trace_summary"]
MAX_SUMMARY_VALUE = 200


class JudgeMaterial:
    """The parts of a run an LLM metric shows its judge, each under its own heading."""

    @classmethod
    def build_prompt_text(cls, context: MetricContext, sections: list[Section]) -> str:
        """Build the run details pasted into the judge's prompt: each chosen section under a '## <section>' heading.

        output and expected are JSON, input_text is the case input and file names, trace_summary lists the tool calls,
        mock calls and validator attempts.
        """
        renderers = {
            "output": lambda: cls._as_json(context.trace.output),
            "expected": lambda: cls._as_json(context.case.expected),
            "input_text": lambda: cls._as_json(
                {"input": context.case.input, "files": [f.name for f in context.case.files]}
            ),
            "trace_summary": lambda: cls._trace_summary(context),
        }
        return "\n\n".join(f"## {section}\n{renderers[section]()}" for section in sections)

    @staticmethod
    def _as_json(value: Any) -> str:
        return json.dumps(value, indent=2, default=str, ensure_ascii=False)

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
