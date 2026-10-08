import re

from pydantic import BaseModel, ConfigDict, Field

from ..base_metric import BaseMetric
from ..metric_context import MetricContext
from ..metric_result import MetricResult
from .judge_material import JudgeMaterial, Section

PROMPT = """Answer a question about an AI agent's work with exactly one of these labels: {labels}.
Reply with the label only.

Question: {question}

{material}"""


class LLMClassifyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    labels: list[str] = Field(min_length=2)
    include: list[Section] = ["output"]


class LLMClassify(BaseMetric):
    """The label a judge model picks for a question about the run, e.g. "Did the agent invent SKUs? yes/no"."""

    NAME = "llm_classify"
    VALUE_TYPE = "label"
    PARAMS = LLMClassifyParams

    def measure(self, context: MetricContext) -> MetricResult:
        if context.judge is None:
            return MetricResult(value=None, details={"reason": "no judge model is configured"})
        prompt = PROMPT.format(
            labels=", ".join(self.params.labels),
            question=self.params.question,
            material=JudgeMaterial.render(context, self.params.include),
        )
        reply = context.judge.complete(prompt)
        label = self._label(reply)
        return MetricResult(
            value=label, details={} if label else {"error": "the reply names no single label", "reply": reply}
        )

    def _label(self, reply: str) -> str | None:
        answer = reply.strip().strip(".\"'`").casefold()
        by_text = {label.casefold(): label for label in self.params.labels}
        if answer in by_text:
            return by_text[answer]
        named = [label for label in self.params.labels if re.search(rf"\b{re.escape(label.casefold())}\b", answer)]
        return named[0] if len(named) == 1 else None
