import re
from typing import ClassVar

from pydantic import Field

from ...suite import SuiteKind
from ..base_metric import BaseMetric
from ..metric_context import MetricContext
from ..metric_result import MetricResult
from .judge_material import JudgeMaterial
from .judge_prompt_params import JudgePromptParams

DEFAULT_PROMPT = """Answer a question about an AI agent's work with exactly one of these labels: {labels}.
Reply with the label only.

Question: {question}

{material}"""


class LLMClassifyParams(JudgePromptParams):
    PLACEHOLDERS: ClassVar[tuple[str, ...]] = ("labels", "question", "material")

    question: str
    labels: list[str] = Field(min_length=2)


class LLMClassify(BaseMetric):
    """Asks a judge model a question about the run and records which of the suite's labels it answered.

    E.g. question "Did the agent invent SKUs?" with labels [yes, no]. The judge sees the run details chosen by `include`;
    a reply that names no single label is recorded as an error. `judge` picks a model other than the suite's judge,
    `prompt`/`prompt_file` replace the built-in prompt (placeholders {labels}, {question}, {material}).
    """

    NAME = "llm_classify"
    VALUE_TYPE = "label"
    PARAMS = LLMClassifyParams

    def supports(self, kind: SuiteKind) -> bool:
        return super().supports(kind) and self.params.fits(kind)

    def measure(self, context: MetricContext) -> MetricResult:
        if context.judge is None:
            return MetricResult(value=None, details={"reason": "no judge model is configured"})
        prompt = (self.params.prompt or DEFAULT_PROMPT).format(
            labels=", ".join(self.params.labels),
            question=self.params.question,
            material=JudgeMaterial.build_prompt_text(context, self.params.include_for(context)),
        )
        reply = context.judge.complete(prompt, self.params.judge)
        label = self._label_from_reply(reply)
        return MetricResult(
            value=label, details={} if label else {"error": "the reply names no single label", "reply": reply}
        )

    def _label_from_reply(self, reply: str) -> str | None:
        answer = reply.strip().strip(".\"'`").casefold()
        by_text = {label.casefold(): label for label in self.params.labels}
        if answer in by_text:
            return by_text[answer]
        named = [label for label in self.params.labels if re.search(rf"\b{re.escape(label.casefold())}\b", answer)]
        return named[0] if len(named) == 1 else None
