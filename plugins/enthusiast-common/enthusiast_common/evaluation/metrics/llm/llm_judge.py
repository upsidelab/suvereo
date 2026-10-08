import json
from statistics import median
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..base_judge_client import BaseJudgeClient
from ..base_metric import BaseMetric
from ..metric_context import MetricContext
from ..metric_result import MetricResult
from .judge_material import JudgeMaterial, Section

SCALES = {"binary": (0, 1, "0 (not met) or 1 (met)"), "1-5": (1, 5, "from 1 (not met at all) to 5 (fully met)")}
PROMPT = """You are grading an AI agent's work against one criterion.

Criterion: {name}: {description}

Score it {scale}. Reply with JSON only: {{"score": <score>, "reasoning": "<one or two sentences>"}}

{material}"""


class Criterion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    weight: float = Field(default=1.0, gt=0)


class LLMJudgeParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criteria: list[Criterion] = Field(min_length=1)
    scale: Literal["binary", "1-5"] = "binary"
    include: list[Section] = ["output", "expected"]
    samples: int = Field(default=1, ge=1, le=9)

    @model_validator(mode="after")
    def _unique_criteria(self) -> "LLMJudgeParams":
        names = [c.name for c in self.criteria]
        if len(names) != len(set(names)):
            raise ValueError("Criterion names must be unique.")
        return self


class LLMJudge(BaseMetric):
    """A judge model's 0-1 score: each criterion is asked separately (median of samples), then weighted together."""

    NAME = "llm_judge"
    VALUE_TYPE = "number"
    PARAMS = LLMJudgeParams

    def measure(self, context: MetricContext) -> MetricResult:
        if context.judge is None:
            return MetricResult(value=None, details={"reason": "no judge model is configured"})
        material = JudgeMaterial.render(context, self.params.include)
        scores, reasoning = {}, {}
        for criterion in self.params.criteria:
            verdicts = [self._ask(context.judge, criterion, material) for _ in range(self.params.samples)]
            graded = sorted((v for v in verdicts if v[0] is not None), key=lambda v: v[0])
            if not graded:
                return MetricResult(value=None, details={"error": f"unreadable judge reply for '{criterion.name}'"})
            scores[criterion.name] = median(score for score, _ in graded)
            reasoning[criterion.name] = graded[len(graded) // 2][1]
        total_weight = sum(c.weight for c in self.params.criteria)
        value = sum(scores[c.name] * c.weight for c in self.params.criteria) / total_weight
        return MetricResult(value=value, components=scores, details={"reasoning": reasoning})

    def _ask(self, judge: BaseJudgeClient, criterion: Criterion, material: str) -> tuple[float | None, str]:
        low, high, scale = SCALES[self.params.scale]
        reply = judge.complete(
            PROMPT.format(name=criterion.name, description=criterion.description, scale=scale, material=material)
        )
        verdict = self._verdict(reply)
        try:
            score = float(verdict["score"])
        except (KeyError, TypeError, ValueError):
            return None, reply
        if not low <= score <= high:
            return None, reply
        return (score - low) / (high - low), str(verdict.get("reasoning", ""))

    @staticmethod
    def _verdict(reply: str) -> dict:
        decoder = json.JSONDecoder()
        for start in (i for i, char in enumerate(reply) if char == "{"):
            try:
                value, _ = decoder.raw_decode(reply, start)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and "score" in value:
                return value
        return {}
