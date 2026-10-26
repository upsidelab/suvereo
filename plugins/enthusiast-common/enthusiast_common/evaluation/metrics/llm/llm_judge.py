import json
from statistics import median
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...suite import SuiteKind
from ..base_judge_client import BaseJudgeClient
from ..base_metric import BaseMetric
from ..metric_context import MetricContext
from ..metric_result import MetricResult
from .judge_material import JudgeMaterial, Section
from .judge_prompt_params import JudgePromptParams

SCALES = {"binary": (0, 1, "0 (not met) or 1 (met)"), "1-5": (1, 5, "from 1 (not met at all) to 5 (fully met)")}
DEFAULT_PROMPT = """You are grading an AI agent's work against one criterion.

Criterion: {name}: {description}

Score it {scale}. Reply with JSON only: {{"score": <score>, "reasoning": "<one or two sentences>"}}

{material}"""


class Criterion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    weight: float = Field(default=1.0, gt=0)


class ScoreRange(BaseModel):
    """A custom score range for the judge, e.g. 0-10; scores are normalised to 0-1."""

    model_config = ConfigDict(extra="forbid")

    min: float
    max: float

    @model_validator(mode="after")
    def _max_above_min(self) -> "ScoreRange":
        if self.max <= self.min:
            raise ValueError("Score range 'max' must be above 'min'.")
        return self


class LLMJudgeParams(JudgePromptParams):
    PLACEHOLDERS: ClassVar[tuple[str, ...]] = ("name", "description", "scale", "material")
    DEFAULT_INCLUDE: ClassVar[dict[SuiteKind, list[Section]]] = {
        "execution": ["outcome", "output", "expected"],
        "conversation": ["outcome", "transcript", "expected"],
    }

    criteria: list[Criterion] = Field(min_length=1)
    scale: Literal["binary", "1-5"] | ScoreRange = "binary"
    samples: int = Field(default=1, ge=1, le=9)

    @model_validator(mode="after")
    def _unique_criteria(self) -> "LLMJudgeParams":
        names = [c.name for c in self.criteria]
        if len(names) != len(set(names)):
            raise ValueError("Criterion names must be unique.")
        return self


class LLMJudge(BaseMetric):
    """Scores the agent's work 0-1 by asking a judge model to grade it against criteria written in the suite.

    Each criterion (e.g. "every line item from the document is ordered") is sent to the judge separately with the run
    details chosen by `include`; the judge replies with a score on the scale and its reasoning. With `samples` > 1 the
    median score is kept. Scores are normalised to 0-1 and averaged by criterion weight; each criterion's score is also
    reported as a component. `judge` picks a model other than the suite's judge, `prompt`/`prompt_file` replace the
    built-in prompt (placeholders {name}, {description}, {scale}, {material}).
    """

    NAME = "llm_judge"
    VALUE_TYPE = "number"
    PARAMS = LLMJudgeParams

    def supports(self, kind: SuiteKind) -> bool:
        return super().supports(kind) and self.params.fits(kind)

    def measure(self, context: MetricContext) -> MetricResult:
        if context.judge is None:
            return MetricResult(value=None, details={"reason": "no judge model is configured"})
        material = JudgeMaterial.build_prompt_text(context, self.params.include_for(context))
        scores, reasoning, unreadable = {}, {}, []
        for criterion in self.params.criteria:
            verdicts = [
                self._ask_judge_for_score(context.judge, criterion, material) for _ in range(self.params.samples)
            ]
            graded = sorted((v for v in verdicts if v[0] is not None), key=lambda v: v[0])
            if not graded:
                unreadable.append(criterion.name)
                continue
            scores[criterion.name] = median(score for score, _ in graded)
            reasoning[criterion.name] = graded[len(graded) // 2][1]
        if unreadable:
            error = f"unreadable judge reply for {', '.join(repr(n) for n in unreadable)}"
            return MetricResult(value=None, components=scores, details={"error": error, "reasoning": reasoning})
        total_weight = sum(c.weight for c in self.params.criteria)
        value = sum(scores[c.name] * c.weight for c in self.params.criteria) / total_weight
        binary = self.params.scale == "binary" and all(score in (0, 1) for score in scores.values())
        return MetricResult(value=value, components=scores, binary_components=binary, details={"reasoning": reasoning})

    def _ask_judge_for_score(
        self, judge: BaseJudgeClient, criterion: Criterion, material: str
    ) -> tuple[float | None, str]:
        low, high, scale = self._score_range()
        prompt = (self.params.prompt or DEFAULT_PROMPT).format(
            name=criterion.name, description=criterion.description, scale=scale, material=material
        )
        reply = judge.complete(prompt, self.params.judge)
        verdict = self._parse_verdict(reply)
        try:
            score = float(verdict["score"])
        except (KeyError, TypeError, ValueError):
            return None, reply
        if not low <= score <= high:
            return None, reply
        return (score - low) / (high - low), str(verdict.get("reasoning", ""))

    def _score_range(self) -> tuple[float, float, str]:
        """The lowest and highest score, and how the prompt describes the scale."""
        scale = self.params.scale
        if isinstance(scale, ScoreRange):
            return scale.min, scale.max, f"from {scale.min:g} (not met at all) to {scale.max:g} (fully met)"
        return SCALES[scale]

    @staticmethod
    def _parse_verdict(reply: str) -> dict:
        decoder = json.JSONDecoder()
        for start in (i for i, char in enumerate(reply) if char == "{"):
            try:
                value, _ = decoder.raw_decode(reply, start)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and "score" in value:
                return value
        return {}
