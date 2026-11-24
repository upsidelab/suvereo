import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent.evaluation.reports.baseline_diff import ValueChange

MAX_INLINE_CHARS = 160


class MarkdownText:
    @staticmethod
    def cell(value: Any) -> str:
        if value is None:
            return "–"
        if isinstance(value, bool):
            return "yes" if value else "no"
        if isinstance(value, float):
            return f"{value:.3g}"
        return str(value)

    @staticmethod
    def usd(value: float | None) -> str:
        return "–" if value is None else f"${value:.4f}"

    @classmethod
    def change(cls, change: "ValueChange") -> str:
        if change.before is None:
            return f"{cls.cell(change.after)} (no baseline)"
        delta = f" ({change.delta:+.3g})" if change.delta else ""
        return f"{cls.cell(change.before)} → {cls.cell(change.after)}{delta}"

    @staticmethod
    def one_line(value: Any) -> str:
        text = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
        text = " ".join(text.split())
        return text if len(text) <= MAX_INLINE_CHARS else text[: MAX_INLINE_CHARS - 1] + "…"

    @classmethod
    def table(cls, header: list[str], rows: list[list[Any]]) -> str:
        cells = [[str(cell).replace("|", "\\|") for cell in row] for row in rows]
        lines = [f"| {' | '.join(header)} |", f"|{'---|' * len(header)}"]
        lines += [f"| {' | '.join(row)} |" for row in cells]
        return "\n".join(lines)
