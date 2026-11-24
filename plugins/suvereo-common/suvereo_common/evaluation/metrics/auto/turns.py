from suvereo_common.evaluation.metrics.auto.run_figure import RunFigure
from suvereo_common.evaluation.metrics.metric_context import MetricContext
from suvereo_common.evaluation.suite import SuiteKind


class Turns(RunFigure):
    """How many user messages the conversation took."""

    NAME = "turns"
    KINDS = (SuiteKind.CONVERSATION,)

    def read_figure(self, context: MetricContext) -> int:
        """Return the conversation's number of turns."""
        return len(context.trace.turns)
