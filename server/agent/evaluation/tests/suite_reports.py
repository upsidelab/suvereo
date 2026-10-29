from enthusiast_common.evaluation.loaded_suite import LoadedSuite
from enthusiast_common.evaluation.metrics import MetricResult
from enthusiast_common.evaluation.suite import AgenticExecutionEvalCase, EvalSuite
from enthusiast_common.evaluation.trace import ExecutionTrace

from agent.evaluation.reports import SuiteReport
from agent.evaluation.runner import RunResult, ThresholdResult
from agent.evaluation.runner.suite_run_result import SuiteRunResult

CASES = [
    AgenticExecutionEvalCase(id="ada", tags=["vip"], description="A regular order"),
    AgenticExecutionEvalCase(id="bob"),
]


def loaded_suite(tmp_path, cases=CASES, **changes) -> LoadedSuite:
    suite = EvalSuite.model_validate(
        {
            "agent": {"type": "order-intake"},
            "models": [{"provider": "OpenAI", "model": "gpt-4.1", "label": "gpt"}],
            "metrics": [
                {
                    "type": "mock_called",
                    "name": "orders",
                    "params": {"method": "create_order"},
                    "pass_threshold": {"min": 1},
                },
                {"type": "json_schema", "name": "valid", "params": {"schema": {"type": "object"}}},
            ],
            "cases": [],
            "min_pass_rate": 0.8,
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
    thresholds = {
        "orders": ThresholdResult(passed=orders >= 1, required=True),
        "valid": ThresholdResult(passed=passed, required=True),
    }
    return RunResult(
        case_id=case_id,
        model=model,
        variant="default",
        repeat=repeat,
        passed=passed,
        metrics=metrics,
        thresholds=thresholds,
        trace=ExecutionTrace(error=error),
    )


JUDGE_METRIC = {
    "type": "llm_judge",
    "name": "judge",
    "params": {"criteria": [{"name": "complete", "description": "d"}]},
}
JUDGE_REASONING = {"complete": "The XL mug was ordered  instead of the regular one.", "no_invented": "All SKUs exist."}


def judged_run(case_id="ada", passed=True):
    """A run that a judge scored, with its reasoning per criterion."""
    run = run_result(case_id, passed=passed, orders=1.0 if passed else 0.0)
    run.metrics["judge"] = MetricResult(
        value=0.5,
        components={"complete": 0.0, "no_invented": 1.0},
        binary_components=True,
        details={"reasoning": JUDGE_REASONING},
    )
    return run


def judged_suite_report(tmp_path, runs, selected=None) -> SuiteReport:
    metrics = [*loaded_suite(tmp_path).suite.model_dump()["metrics"], JUDGE_METRIC]
    judge = {"provider": "OpenAI", "model": "gpt-4.1-mini"}
    return suite_report(tmp_path, runs, selected, metrics=metrics, judge=judge)


def suite_report(tmp_path, runs, selected=None, git=None, baseline=None, **suite_changes) -> SuiteReport:
    result = SuiteRunResult(suite="orders", planned_runs=len(runs), runs=runs, spent_usd=0.0)
    return SuiteReport(loaded_suite(tmp_path, **suite_changes), result, selected, git=git, baseline=baseline)
