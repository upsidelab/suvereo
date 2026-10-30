import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .baseline_diff import ValueChange

MAX_INLINE_CHARS = 160


class MarkdownText:
    """Formats values and tables for report.md: numbers to 3 significant digits, missing values as '–', long values
    cut short, and '|' escaped inside table cells."""

    @staticmethod
    def cell(value: Any) -> str:
        """A value as table or list text: 3 significant digits, yes/no, '–' when missing."""
        if value is None:
            return "–"
        if isinstance(value, bool):
            return "yes" if value else "no"
        if isinstance(value, float):
            return f"{value:.3g}"
        return str(value)

    @staticmethod
    def usd(value: float | None) -> str:
        """An amount in USD to 4 decimals, '–' when unknown."""
        return "–" if value is None else f"${value:.4f}"

    @classmethod
    def change(cls, change: "ValueChange") -> str:
        """A figure's move from a baseline run, e.g. '0.8 → 0.9 (+0.1)'; just the new value when it is new."""
        if change.before is None:
            return f"{cls.cell(change.after)} (new)"
        delta = f" ({change.delta:+.3g})" if change.delta else ""
        return f"{cls.cell(change.before)} → {cls.cell(change.after)}{delta}"

    @staticmethod
    def one_line(value: Any) -> str:
        """A value on one line, as JSON unless it is text, cut to MAX_INLINE_CHARS characters."""
        text = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
        text = " ".join(text.split())
        return text if len(text) <= MAX_INLINE_CHARS else text[: MAX_INLINE_CHARS - 1] + "…"

    @classmethod
    def table(cls, header: list[str], rows: list[list[Any]]) -> str:
        """A Markdown table; cells must already be text or numbers ready to print."""
        cells = [[str(cell).replace("|", "\\|") for cell in row] for row in rows]
        lines = [f"| {' | '.join(header)} |", f"|{'---|' * len(header)}"]
        lines += [f"| {' | '.join(row)} |" for row in cells]
        return "\n".join(lines)
