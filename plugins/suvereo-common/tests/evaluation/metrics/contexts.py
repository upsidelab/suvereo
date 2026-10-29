from datetime import datetime

from suvereo_common.agentic_execution import ExecutionResult
from suvereo_common.evaluation.metrics import MetricContext
from suvereo_common.evaluation.suite import EvalCase
from suvereo_common.evaluation.trace import ExecutionTrace, MockCall


def mock_call(method: str, **arguments) -> MockCall:
    return MockCall(method=method, arguments=arguments, started_at=datetime(2026, 1, 1))


def run(
    output=None, expected=None, success=True, failure_code=None, error=None, kind="execution", **trace_fields
) -> MetricContext:
    result = None if error else ExecutionResult(success=success, output=output or {}, failure_code=failure_code)
    trace = ExecutionTrace(output=output, execution_result=result, error=error, **trace_fields)
    return MetricContext(trace=trace, case=EvalCase(id="case", expected=expected or {}), kind=kind)
