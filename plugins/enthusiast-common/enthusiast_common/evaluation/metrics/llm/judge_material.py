import json
from typing import Any, Literal

from ..metric_context import MetricContext

Section = Literal["output", "expected", "input_text", "trace_summary"]
MAX_SUMMARY_VALUE = 200


class JudgeMaterial:
    """The parts of a run an LLM metric shows its judge, each under its own heading."""

    @classmethod
    def render(cls, context: MetricContext, sections: list[Section]) -> str:
        """The chosen sections of a run as prompt text, one headed block each."""
        renderers = {
            "output": lambda: cls._json(context.trace.output),
            "expected": lambda: cls._json(context.case.expected),
            "input_text": lambda: cls._json(
                {"input": context.case.input, "files": [f.name for f in context.case.files]}
            ),
            "trace_summary": lambda: cls._summary(context),
        }
        return "\n\n".join(f"## {section}\n{renderers[section]()}" for section in sections)

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, indent=2, default=str, ensure_ascii=False)

    @classmethod
    def _summary(cls, context: MetricContext) -> str:
        trace = context.trace
        lines = [f"tool {c.name}({cls._short(c.args)}) -> {cls._short(c.error or c.output)}" for c in trace.tool_calls]
        lines += [
            f"mock {c.method}({cls._short(c.arguments)}) -> {cls._short(c.error or c.result)}" for c in trace.mock_calls
        ]
        lines += [
            f"attempt {a.number}: {'passed' if a.passed else f'failed: {a.validator_feedback}'}" for a in trace.attempts
        ]
        return "\n".join(lines) or "(nothing happened)"

    @staticmethod
    def _short(value: Any) -> str:
        text = json.dumps(value, default=str, ensure_ascii=False) if not isinstance(value, str) else value
        return text if len(text) <= MAX_SUMMARY_VALUE else text[:MAX_SUMMARY_VALUE] + "…"
