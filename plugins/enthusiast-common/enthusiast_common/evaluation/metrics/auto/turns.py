from ...suite import SuiteKind
from ..metric_context import MetricContext
from .run_figure import RunFigure


class Turns(RunFigure):
    """How many user messages the conversation took."""

    NAME = "turns"
    KINDS = (SuiteKind.CONVERSATION,)

    def read_figure(self, context: MetricContext) -> int:
        return len(context.trace.turns)
