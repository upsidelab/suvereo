from pydantic import BaseModel, ConfigDict, field_validator
from suvereo_common.agentic_execution import StopExecutionValidator
from suvereo_common.evaluation.metrics.base_metric import BaseMetric
from suvereo_common.evaluation.metrics.metric_context import MetricContext
from suvereo_common.evaluation.metrics.metric_result import MetricResult
from suvereo_common.evaluation.suite import SuiteKind

EVENTS = ("retry", "tool_error", "validator_failed", "stop_execution")
#: Events of the validator loop, which only executions have.
EXECUTION_EVENTS = ("retry", "validator_failed", "stop_execution")


class TraceEventParams(BaseModel):
    """Settings for the trace event metric."""

    model_config = ConfigDict(extra="forbid")

    event: str

    @field_validator("event")
    @classmethod
    def _validate_event_name(cls, event: str) -> str:
        name, _, code = event.partition(":")
        if name not in EVENTS or (code and name != "validator_failed"):
            raise ValueError(f"Unknown event '{event}'; use one of {', '.join(EVENTS)}, or validator_failed:<code>.")
        return event


class TraceEvent(BaseMetric):
    """Whether something happened during the run: retry, tool_error, validator_failed[:code] or stop_execution."""

    NAME = "trace_event"
    VALUE_TYPE = "bool"
    PARAMS = TraceEventParams

    def supports(self, kind: SuiteKind) -> bool:
        """Return whether this metric can measure the given kind of suite."""
        return kind == SuiteKind.EXECUTION or self.params.event.partition(":")[0] not in EXECUTION_EVENTS

    def measure(self, context: MetricContext) -> MetricResult:
        """Check whether the run's trace contains the event."""
        name, _, code = self.params.event.partition(":")
        trace = context.trace
        happened = {
            "retry": trace.had_retry,
            "tool_error": trace.had_tool_error,
            "validator_failed": lambda: trace.had_validator_failure(code or None),
            "stop_execution": lambda: bool(trace.tool_calls_named(StopExecutionValidator.TOOL_NAME)),
        }[name]()
        return MetricResult(value=happened)
