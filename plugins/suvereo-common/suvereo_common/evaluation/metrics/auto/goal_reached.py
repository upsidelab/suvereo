from ...json_reply import JsonReply
from ...suite import ConversationEvalCase, SuiteKind
from ..base_metric import BaseMetric
from ..llm.judge_material import JudgeMaterial
from ..metric_context import MetricContext
from ..metric_result import MetricResult

PROMPT = """A simulated user chatted with an AI assistant to reach a goal. Decide from the transcript whether the
goal was reached, whatever the user said at the end.

Goal: {goal}

Reply with JSON only: {{"reached": true | false, "reasoning": "<one or two sentences>"}}

{material}"""


class GoalReached(BaseMetric):
    """Whether the simulated user reached its goal, as the suite's judge reads the transcript; none for a case with no
    goal."""

    NAME = "goal_reached"
    VALUE_TYPE = "bool"
    KINDS = (SuiteKind.CONVERSATION,)

    def measure(self, context: MetricContext) -> MetricResult:
        case = context.case
        if not isinstance(case, ConversationEvalCase) or case.simulated_user is None or not case.simulated_user.goal:
            return MetricResult(value=None, details={"reason": "the case has no simulated user goal"})
        if not context.trace.turns:
            return MetricResult(value=False, details={"reasoning": "the conversation never started"})
        if context.judge is None:
            return MetricResult(value=None, details={"reason": "no judge model is configured"})
        material = JudgeMaterial.build_prompt_text(context, ["transcript"])
        reply = context.judge.complete(PROMPT.format(goal=case.simulated_user.goal, material=material))
        verdict = self._verdict(reply)
        if verdict is None:
            return MetricResult(value=None, details={"error": "unreadable judge reply", "reply": reply})
        return MetricResult(value=verdict["reached"], details={"reasoning": str(verdict.get("reasoning", ""))})

    @staticmethod
    def _verdict(reply: str) -> dict | None:
        return next((value for value in JsonReply.objects(reply) if isinstance(value.get("reached"), bool)), None)
