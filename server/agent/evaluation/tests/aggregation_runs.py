from enthusiast_common.evaluation.metrics import MetricResult
from enthusiast_common.evaluation.trace import ExecutionTrace

from agent.evaluation.runner import RunResult


def run(case_id="a", model="m", variant="default", repeat=1, passed=True, components=None, **metrics) -> RunResult:
    """A finished run with the given metric values (attempts defaults to 1); components go on the first given one."""
    results = {name: MetricResult(value=value) for name, value in {"attempts": 1.0, **metrics}.items()}
    if components:
        first = next(iter(metrics))
        results[first] = MetricResult(value=results[first].value, components=components)
    return RunResult(
        case_id=case_id,
        model=model,
        variant=variant,
        repeat=repeat,
        passed=passed,
        metrics=results,
        gates={},
        trace=ExecutionTrace(),
    )
