import json
import subprocess

from enthusiast_common.evaluation.suite import EvalCase
from enthusiast_common.evaluation.trace import ExecutionTrace, ToolCall

from agent.evaluation.reports import ExitCode, GitState, ReportMdWriter, SuiteReport, SuiteVerdict, SummaryJsonWriter
from agent.evaluation.runner import GateResult
from agent.evaluation.runner.suite_run_result import SuiteRunResult

from .suite_reports import loaded_suite, run_result, suite_report


def _flaky_and_failing_runs():
    failing = run_result("bob", passed=False, orders=0.0, error="Out of stock")
    failing.trace = ExecutionTrace(
        error="Out of stock", tool_calls=[ToolCall(run_id="t", name="place_order", args={"sku": "A"}, error="409")]
    )
    return [run_result("ada", repeat=1), run_result("ada", repeat=2, passed=False), failing]


class TestSuiteVerdict:
    def test_passes_when_every_candidate_reaches_the_pass_threshold(self, tmp_path):
        verdict = SuiteVerdict.of(suite_report(tmp_path, [run_result("ada"), run_result("bob")]))

        assert (verdict.status, verdict.exit_code, verdict.below_threshold) == ("complete", ExitCode.PASSED, [])

    def test_a_candidate_below_the_threshold_fails_the_run(self, tmp_path):
        verdict = SuiteVerdict.of(suite_report(tmp_path, [run_result("ada"), run_result("bob", passed=False)]))

        assert (verdict.exit_code, verdict.below_threshold) == (ExitCode.BELOW_PASS_THRESHOLD, ["gpt/default"])

    def test_a_run_stopped_by_the_budget_is_partial(self, tmp_path):
        result = SuiteRunResult(
            suite="orders", planned_runs=4, runs=[run_result("ada")], spent_usd=1.0, stopped_reason="budget_spent"
        )

        verdict = SuiteVerdict.of(SuiteReport(loaded_suite(tmp_path), result))

        assert (verdict.status, verdict.exit_code) == ("partial", ExitCode.BUDGET_EXCEEDED)

    def test_an_untracked_budget_after_every_planned_run_is_not_a_budget_stop(self, tmp_path):
        runs = [run_result("ada"), run_result("bob")]
        result = SuiteRunResult(
            suite="orders", planned_runs=2, runs=runs, spent_usd=0.1, stopped_reason="budget_untracked"
        )

        verdict = SuiteVerdict.of(SuiteReport(loaded_suite(tmp_path), result))

        assert (verdict.status, verdict.exit_code) == ("complete", ExitCode.PASSED)


class TestSummaryJsonWriter:
    def test_optional_gates_are_listed_apart_from_the_ones_that_failed_the_run(self, tmp_path):
        run = run_result("ada", passed=False)
        run.gates["orders"] = GateResult(passed=False, required=False)

        [path] = SummaryJsonWriter().write(suite_report(tmp_path, [run]), tmp_path)

        [failing] = json.loads(path.read_text())["failing_runs"]
        assert (failing["failed_gates"], failing["failed_optional_gates"]) == (["valid"], ["orders"])

    def test_holds_the_verdict_candidates_gates_failing_runs_and_cost(self, tmp_path):
        report = suite_report(tmp_path, _flaky_and_failing_runs(), git=GitState(sha="abc", dirty=True))

        [path] = SummaryJsonWriter().write(report, tmp_path)

        summary = json.loads(path.read_text())
        assert (summary["status"], summary["exit_code"], summary["git"]) == (
            "complete",
            1,
            {"sha": "abc", "dirty": True},
        )
        [candidate] = summary["candidates"]
        assert (candidate["candidate"], candidate["pass_rate"], candidate["below_threshold"]) == (
            "gpt/default",
            1 / 3,
            True,
        )
        assert candidate["metrics"] == {"orders": 2 / 3, "valid": 1 / 3}
        assert summary["gates"]["orders"] == {
            "gates": ["min 1.0"],
            "passed_runs": 2,
            "gated_runs": 3,
            "pass_rate": 2 / 3,
        }
        assert [(r["case_id"], r["failed_gates"]) for r in summary["failing_runs"]] == [
            ("ada", ["valid"]),
            ("bob", ["orders", "valid"]),
        ]
        assert summary["cost"]["spent_usd"] == 0.0


class TestReportMdWriter:
    def test_explains_the_verdict_comparison_failures_and_flaky_cases(self, tmp_path):
        [path] = ReportMdWriter().write(suite_report(tmp_path, _flaky_and_failing_runs()), tmp_path)

        text = path.read_text()
        assert "Some candidates are below the pass threshold (80%); exit code 1" in text
        assert "| gpt/default | 3 | 0.333 |" in text
        assert "### valid — 2 run(s)" in text
        assert "  - value: no (gate: equals true)" in text
        assert '  - trace: place_order({"sku": "A"}) → 409' in text
        assert "  - error: Out of stock" in text
        assert "| ada | gpt/default | 1/2 |" in text
        assert "## Metrics per tag" in text and "| vip | gpt/default |" in text
        assert "ran fewer than 5 times" in text

    def test_each_failed_run_shows_the_gate_its_case_was_checked_against(self, tmp_path):
        cases = [
            EvalCase(id="ada"),
            EvalCase(
                id="bob",
                metrics=[{"type": "mock_called", "name": "orders", "params": {"method": "m"}, "gate": {"min": 3}}],
            ),
        ]
        runs = [run_result("ada", passed=False, orders=0.0), run_result("bob", passed=False, orders=2.0)]
        report = SuiteReport(
            loaded_suite(tmp_path, cases=cases), SuiteRunResult(suite="o", planned_runs=2, runs=runs, spent_usd=0)
        )
        runs[1].gates["orders"] = GateResult(passed=False, required=True)

        [path] = ReportMdWriter().write(report, tmp_path)

        text = path.read_text()
        assert "  - value: 0 (gate: min 1.0)" in text and "  - value: 2 (gate: min 3.0)" in text

    def test_an_untracked_budget_has_its_own_verdict_without_the_threshold(self, tmp_path):
        result = SuiteRunResult(
            suite="orders", planned_runs=3, runs=[run_result("ada")], spent_usd=0.1, stopped_reason="budget_untracked"
        )

        [path] = ReportMdWriter().write(SuiteReport(loaded_suite(tmp_path), result), tmp_path)

        assert "because a call could not be priced, so the budget could not be tracked; exit code 3" in path.read_text()

    def test_a_run_where_everything_passed_has_no_failures_section(self, tmp_path):
        [path] = ReportMdWriter().write(suite_report(tmp_path, [run_result("ada"), run_result("bob")]), tmp_path)

        text = path.read_text()
        assert "Every candidate reached the pass threshold" in text
        assert "## Failures" not in text and "## Flaky cases" not in text


class TestGitState:
    def test_is_empty_outside_a_git_checkout(self, tmp_path):
        assert GitState.of(tmp_path) == GitState()

    def test_records_the_commit_and_uncommitted_changes(self, tmp_path):
        git = ["git", "-C", str(tmp_path), "-c", "user.email=e@x", "-c", "user.name=e"]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "start"], check=True)
        (tmp_path / "suite.yaml").write_text("x")

        state = GitState.of(tmp_path)

        assert len(state.sha) == 40 and state.dirty is True
