from enthusiast_common.evaluation.metrics import MetricResult

from .markdown_text import MarkdownText

REASONING = "reasoning"


class JudgeReasoning:
    """The reasons a judge metric (llm_judge) gave for each criterion's score, kept in its details."""

    @staticmethod
    def by_criterion(result: MetricResult) -> dict[str, str]:
        """Each criterion's reasoning on one line; empty for metrics that give none."""
        reasoning = result.details.get(REASONING)
        if not isinstance(reasoning, dict):
            return {}
        return {name: " ".join(str(reason).split()) for name, reason in reasoning.items()}

    @classmethod
    def lines(cls, result: MetricResult) -> list[str]:
        """One line per criterion with its score, e.g. 'completeness (success): Every item was ordered.'"""
        return [cls._line(result, name, reason) for name, reason in cls.by_criterion(result).items()]

    @staticmethod
    def outcome(score: float) -> str:
        """A binary component's score in words."""
        return "success" if score else "failure"

    @classmethod
    def _line(cls, result: MetricResult, name: str, reason: str) -> str:
        score = result.components.get(name)
        if result.binary_components and score is not None:
            return f"{name} ({cls.outcome(score)}): {reason}"
        return f"{name} {MarkdownText.cell(score)}: {reason}"
