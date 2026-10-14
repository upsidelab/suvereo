from enthusiast_common.evaluation.loaded_suite import LoadedSuite
from enthusiast_common.evaluation.metrics import MetricResult
from enthusiast_common.evaluation.suite import EvalCase, EvalSuite
from enthusiast_common.evaluation.trace import ExecutionTrace

from agent.evaluation.reports import SuiteReport
from agent.evaluation.runner import GateResult, RunResult
from agent.evaluation.runner.suite_run_result import SuiteRunResult

CASES = [EvalCase(id="ada", tags=["vip"], description="A regular order"), EvalCase(id="bob")]


def loaded_suite(tmp_path, cases=CASES, **changes) -> LoadedSuite:
    suite = EvalSuite.model_validate(
        {
            "agent": {"type": "order-intake"},
            "models": [{"provider": "OpenAI", "model": "gpt-4.1", "label": "gpt"}],
            "metrics": [
                {"type": "mock_called", "name": "orders", "params": {"method": "create_order"}, "gate": {"min": 1}},
                {"type": "json_schema", "name": "valid", "params": {"schema": {"type": "object"}}},
            ],
            "cases": [],
            **changes,
        }
    )
    return LoadedSuite(path=tmp_path / "suite.yaml", suite=suite, cases=cases)


def run_result(case_id, model="gpt", repeat=1, passed=True, cost=0.01, orders=1.0, error=None):
    metrics = {
        "attempts": MetricResult(value=1.0),
        "cost_usd": MetricResult(value=cost),
        "duration_s": MetricResult(value=2.0),
        "judge_cost_usd": MetricResult(value=0.0),
        "orders": MetricResult(value=orders, components={"precision": 0.5}),
        "valid": MetricResult(value=passed),
    }
    gates = {"orders": GateResult(passed=orders >= 1, required=True), "valid": GateResult(passed=passed, required=True)}
    return RunResult(
        case_id=case_id,
        model=model,
        variant="default",
        repeat=repeat,
        passed=passed,
        metrics=metrics,
        gates=gates,
        trace=ExecutionTrace(error=error),
    )


def suite_report(tmp_path, runs, selected=None, git=None, **suite_changes) -> SuiteReport:
    result = SuiteRunResult(suite="orders", planned_runs=len(runs), runs=runs, spent_usd=0.0)
    return SuiteReport(loaded_suite(tmp_path, **suite_changes), result, selected, git=git)
