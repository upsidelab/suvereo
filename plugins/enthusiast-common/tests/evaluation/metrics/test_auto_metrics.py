import pytest
from enthusiast_common.evaluation.metrics.auto import (
    Attempts,
    CostUsd,
    ExecutionSucceeded,
    FailureCode,
    FirstAttemptSuccess,
    InputTokens,
    LLMCalls,
)
from enthusiast_common.evaluation.trace import Attempt, LLMCall

from .contexts import run

PASSED, FAILED = Attempt(number=1, response="", passed=True), Attempt(number=1, response="", passed=False)


class TestOutcomeMetrics:
    @pytest.mark.parametrize(
        "context, succeeded",
        [
            (run(success=True), True),
            (run(success=False, failure_code="VALIDATION_FAILED"), False),
            (run(error="RuntimeError: boom"), False),
            (run(success=False, failure_code="MISSING_SKU", expected={"failure_code": "MISSING_SKU"}), True),
            (run(success=False, failure_code="OTHER", expected={"failure_code": "MISSING_SKU"}), False),
            (run(success=True, expected={"failure_code": "MISSING_SKU"}), False),
        ],
    )
    def test_execution_succeeded_follows_what_the_case_expects(self, context, succeeded):
        assert ExecutionSucceeded().measure(context).value is succeeded

    @pytest.mark.parametrize(
        "context, code",
        [(run(success=True), None), (run(success=False, failure_code="X"), "X"), (run(error="E: x"), "RUNTIME_ERROR")],
    )
    def test_failure_code_labels_the_outcome(self, context, code):
        assert FailureCode().measure(context).value == code

    def test_attempt_metrics(self):
        retried = run(success=True, attempts=[FAILED, PASSED.model_copy(update={"number": 2})])

        assert Attempts().measure(retried).value == 2.0
        assert FirstAttemptSuccess().measure(retried).value is False
        assert FirstAttemptSuccess().measure(run(success=True, attempts=[PASSED])).value is True


class TestRunFigures:
    def test_figures_come_from_the_trace_and_the_runner(self):
        context = run(llm_calls=[LLMCall(run_id="a", input_tokens=10), LLMCall(run_id="b", input_tokens=5)])
        context.cost_usd = 0.02

        assert (InputTokens().measure(context).value, LLMCalls().measure(context).value) == (15.0, 2.0)
        assert CostUsd().measure(context).value == 0.02

    def test_a_missing_figure_is_not_measured_rather_than_zero(self):
        assert CostUsd().measure(run()).value is None
