from pydantic import BaseModel, ConfigDict

from ..suite import EvalCase, SuiteKind
from ..trace import ExecutionTrace
from .base_judge_client import BaseJudgeClient


class MetricContext(BaseModel):
    """What a metric measures: one run's trace, the case it ran and the kind of suite it belongs to, run figures the
    runner works out, and the judge."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    trace: ExecutionTrace
    case: EvalCase
    kind: SuiteKind
    duration_s: float | None = None
    cost_usd: float | None = None
    judge: BaseJudgeClient | None = None
