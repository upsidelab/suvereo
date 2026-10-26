import pytest
from enthusiast_common.evaluation.metrics.auto import (
    AUTO_METRICS,
    Attempts,
    ConversationCompleted,
    ConversationEnd,
    CostUsd,
    ExecutionSucceeded,
    FailureCode,
    FirstAttemptSuccess,
    InputTokens,
    LLMCalls,
    Turns,
    auto_metrics_for,
)
from enthusiast_common.evaluation.trace import Attempt, LLMCall, Turn

from .contexts import run

PASSED, FAILED = Attempt(number=1, response="", passed=True), Attempt(number=1, response="", passed=False)
ANSWERED = [Turn(user_message="Hi", answer="Hello"), Turn(user_message="Bye", answer="Bye")]


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


class TestConversationMetrics:
    @pytest.mark.parametrize(
        "fields, completed",
        [
            ({"turns": ANSWERED, "ended_by": "done"}, True),
            ({"turns": ANSWERED, "ended_by": "gave_up"}, False),
            ({"turns": ANSWERED, "ended_by": "max_turns"}, False),
            ({"turns": [], "ended_by": "done"}, False),
            (
                {"turns": [Turn(user_message="Hi", error="RuntimeError: boom")], "error": "RuntimeError: boom"},
                False,
            ),
            ({"turns": ANSWERED[:1], "error": "RuntimeError: bad simulator", "ended_by": "error"}, False),
        ],
    )
    def test_conversation_completed_needs_every_turn_answered_and_the_user_done(self, fields, completed):
        assert ConversationCompleted().measure(run(**fields)).value is completed

    @pytest.mark.parametrize(
        "fields, end",
        [
            ({"ended_by": "done"}, "done"),
            ({"ended_by": "gave_up"}, "gave_up"),
            ({"ended_by": "max_turns"}, "max_turns"),
            ({"error": "RuntimeError: sandbox down"}, "error"),
        ],
    )
    def test_conversation_end_labels_how_the_conversation_ended(self, fields, end):
        assert ConversationEnd().measure(run(**fields)).value == end

    def test_turns_counts_the_user_messages(self):
        context = run(turns=ANSWERED)

        assert Turns().measure(context).value == 2.0


class TestAutoMetricsPerKind:
    def test_each_kind_gets_its_outcome_metrics_and_both_get_the_run_figures(self):
        execution = {m.NAME for m in auto_metrics_for("execution")}
        conversation = {m.NAME for m in auto_metrics_for("conversation")}

        assert {"execution_succeeded", "failure_code", "attempts", "first_attempt_success"} <= execution - conversation
        assert {"conversation_completed", "conversation_end", "turns"} <= conversation - execution
        assert {"duration_s", "cost_usd", "llm_calls", "tool_calls"} <= execution & conversation
        assert execution | conversation == {m.NAME for m in AUTO_METRICS}


class TestRunFigures:
    def test_figures_come_from_the_trace_and_the_runner(self):
        context = run(llm_calls=[LLMCall(run_id="a", input_tokens=10), LLMCall(run_id="b", input_tokens=5)])
        context.cost_usd = 0.02

        assert (InputTokens().measure(context).value, LLMCalls().measure(context).value) == (15.0, 2.0)
        assert CostUsd().measure(context).value == 0.02

    def test_a_missing_figure_is_not_measured_rather_than_zero(self):
        assert CostUsd().measure(run()).value is None
