from pydantic import BaseModel, ConfigDict

from ..base_model_client import BaseModelClient
from ..suite import EvalCase, SuiteKind
from ..trace import ExecutionTrace


class MetricContext(BaseModel):
    """What a metric measures: one run's trace, the case it ran and the kind of suite it belongs to, run figures the
    runner works out, and the judge."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    trace: ExecutionTrace
    case: EvalCase
    kind: SuiteKind
    duration_s: float | None = None
    cost_usd: float | None = None
    judge: BaseModelClient | None = None

    def unjudged_reason(self) -> str | None:
        """Why an LLM metric asks no judge: none is configured, or the run raised before it answered anything."""
        if self.judge is None:
            return "no judge model is configured"
        if self.trace.error is not None and not self.answered:
            return "the run raised before it answered, so there is nothing to judge"
        return None

    @property
    def answered(self) -> bool:
        """Whether the agent answered: a conversation turn with an answer, or an execution's output."""
        if self.kind == SuiteKind.CONVERSATION:
            return any(turn.answer is not None for turn in self.trace.turns)
        return self.trace.output is not None
