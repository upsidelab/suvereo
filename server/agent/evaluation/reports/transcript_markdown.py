from suvereo_common.evaluation.trace import ExecutionTrace, Turn

from .markdown_text import MarkdownText

#: How many of a failed conversation's last turns report.md shows.
LAST_TURNS = 2


class TranscriptMarkdown:
    """A conversation run as Markdown: the whole dialogue for the transcripts report, or its last turns for report.md.
    Messages are quoted, so an answer's own headings and lists stay inside it."""

    @staticmethod
    def ending(trace: ExecutionTrace) -> str:
        """How the conversation ended and after how many turns, e.g. 'gave_up after 3 turn(s)'; 'never started' for a
        run that failed before it."""
        if trace.stop_reason is None:
            return "never started"
        return f"{trace.stop_reason} after {len(trace.turns)} turn(s)"

    @classmethod
    def turns(cls, trace: ExecutionTrace) -> str:
        """Every turn under its own heading: the user's message, the tools the agent called, and its answer."""
        return "\n\n".join(cls._turn(trace, number, turn) for number, turn in enumerate(trace.turns, start=1))

    @staticmethod
    def last_turns(trace: ExecutionTrace) -> list[str]:
        """The last LAST_TURNS turns as one-line list items, for a failed run in report.md."""
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
