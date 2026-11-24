from suvereo_common.evaluation.trace import ExecutionTrace, Turn

from agent.evaluation.reports.markdown_text import MarkdownText

#: How many of a failed conversation's last turns report.md shows.
LAST_TURNS = 2


class TranscriptMarkdown:
    @staticmethod
    def ending(trace: ExecutionTrace) -> str:
        if trace.stop_reason is None:
            return "never started"
        return f"{trace.stop_reason} after {len(trace.turns)} turn(s)"

    @classmethod
    def turns(cls, trace: ExecutionTrace) -> str:
        return "\n\n".join(cls._turn(trace, number, turn) for number, turn in enumerate(trace.turns, start=1))

    @staticmethod
    def last_turns(trace: ExecutionTrace) -> list[str]:
        start = max(len(trace.turns) - LAST_TURNS, 0)
        lines = []
        for number, turn in enumerate(trace.turns[start:], start=start + 1):
            lines.append(f"**user** (turn {number}): {MarkdownText.one_line(turn.user_message)}")
            if turn.answer is not None:
                lines.append(f"**agent**: {MarkdownText.one_line(turn.answer)}")
            else:
                lines.append(f"**agent raised**: {MarkdownText.one_line(turn.error or '')}")
        return lines

    @classmethod
    def _turn(cls, trace: ExecutionTrace, number: int, turn: Turn) -> str:
        parts = [f"## Turn {number}", "**User**", cls._quoted(turn.user_message)]
        tools = [f"{call.name} (raised)" if call.error else call.name for call in trace.tool_calls_in(turn)]
        if tools:
            parts.append(f"<small>tools called: {', '.join(tools)}</small>")
        if turn.answer is not None:
            parts += ["**Agent**", cls._quoted(turn.answer)]
        else:
            parts += ["**Agent raised**", cls._quoted(turn.error or "")]
        return "\n\n".join(parts)

    @staticmethod
    def _quoted(text: str) -> str:
        return "\n".join(f"> {line}".rstrip() for line in text.splitlines()) or ">"
