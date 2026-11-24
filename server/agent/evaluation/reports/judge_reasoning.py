from suvereo_common.evaluation.metrics import MetricResult

from agent.evaluation.reports.markdown_text import MarkdownText

REASONING = "reasoning"


class JudgeReasoning:
    @staticmethod
    def by_criterion(result: MetricResult) -> dict[str, str]:
        reasoning = result.details.get(REASONING)
        if not isinstance(reasoning, dict):
            return {}
        return {name: " ".join(str(reason).split()) for name, reason in reasoning.items()}

    @classmethod
    def lines(cls, result: MetricResult) -> list[str]:
        return [cls._line(result, name, reason) for name, reason in cls.by_criterion(result).items()]

    @staticmethod
    def outcome(score: float) -> str:
        return "success" if score else "failure"

    @classmethod
    def _line(cls, result: MetricResult, name: str, reason: str) -> str:
        score = result.components.get(name)
        if result.binary_components and score is not None:
            return f"{name} ({cls.outcome(score)}): {reason}"
        return f"{name} {MarkdownText.cell(score)}: {reason}"
