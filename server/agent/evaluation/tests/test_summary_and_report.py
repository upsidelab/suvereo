import json
import subprocess

from enthusiast_common.evaluation.suite import EvalCase
from enthusiast_common.evaluation.trace import ExecutionTrace, ToolCall

from agent.evaluation.reports import ExitCode, GitState, ReportMdWriter, SuiteReport, SuiteVerdict, SummaryJsonWriter
from agent.evaluation.runner import ThresholdResult
from agent.evaluation.runner.suite_run_result import SuiteRunResult

from .suite_reports import judged_run, judged_suite_report, loaded_suite, run_result, suite_report


def _flaky_and_failing_runs():
    failing = run_result("bob", passed=False, orders=0.0, error="Out of stock")
    failing.trace = ExecutionTrace(
        error="Out of stock", tool_calls=[ToolCall(run_id="t", name="place_order", args={"sku": "A"}, error="409")]
    )
    return [run_result("ada", repeat=1), run_result("ada", repeat=2, passed=False), failing]


class TestSuiteVerdict:
    def test_passes_when_every_candidate_reaches_the_min_pass_rate(self, tmp_path):
        verdict = SuiteVerdict.of(suite_report(tmp_path, [run_result("ada"), run_result("bob")]))

        assert (verdict.status, verdict.exit_code, verdict.below_min_pass_rate) == ("complete", ExitCode.PASSED, [])

    def test_a_candidate_below_the_threshold_fails_the_run(self, tmp_path):
        verdict = SuiteVerdict.of(suite_report(tmp_path, [run_result("ada"), run_result("bob", passed=False)]))

        assert (verdict.exit_code, verdict.below_min_pass_rate) == (ExitCode.BELOW_MIN_PASS_RATE, ["gpt/default"])

    def test_without_a_min_pass_rate_no_candidate_fails_the_run(self, tmp_path):
        report = suite_report(tmp_path, [run_result("ada", passed=False)], min_pass_rate=None)

        verdict = SuiteVerdict.of(report)

        assert (verdict.exit_code, verdict.below_min_pass_rate) == (ExitCode.PASSED, [])

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
    def test_optional_thresholds_are_listed_apart_from_the_ones_that_failed_the_run(self, tmp_path):
        run = run_result("ada", passed=False)
        run.thresholds["orders"] = ThresholdResult(passed=False, required=False)

        [path] = SummaryJsonWriter().write(suite_report(tmp_path, [run]), tmp_path)

        [failing] = json.loads(path.read_text())["failing_runs"]
        assert (failing["failed_thresholds"], failing["failed_optional_thresholds"]) == (["valid"], ["orders"])

    def test_holds_the_verdict_candidates_thresholds_failing_runs_and_cost(self, tmp_path):
        report = suite_report(tmp_path, _flaky_and_failing_runs(), git=GitState(sha="abc", dirty=True))

        [path] = SummaryJsonWriter().write(report, tmp_path)

        summary = json.loads(path.read_text())
        assert (summary["status"], summary["exit_code"], summary["git"]) == (
            "complete",
            1,
            {"sha": "abc", "dirty": True},
        )
        [candidate] = summary["candidates"]
        assert (candidate["candidate"], candidate["pass_rate"], candidate["below_min_pass_rate"]) == (
            "gpt/default",
            1 / 3,
            True,
        )
        assert candidate["metrics"] == {"orders": 2 / 3, "valid": 1 / 3}
        assert summary["thresholds"]["orders"] == {
            "thresholds": ["min 1.0"],
            "passed_runs": 2,
            "checked_runs": 3,
            "pass_rate": 2 / 3,
        }
        assert [(r["case_id"], r["failed_thresholds"]) for r in summary["failing_runs"]] == [
            ("ada", ["valid"]),
            ("bob", ["orders", "valid"]),
        ]
        assert summary["cost"]["spent_usd"] == 0.0


class TestReportMdWriter:
    def test_explains_the_verdict_comparison_failures_and_flaky_cases(self, tmp_path):
        [path] = ReportMdWriter().write(suite_report(tmp_path, _flaky_and_failing_runs()), tmp_path)

        text = path.read_text()
        assert "## Verdict\n**❌ FAILED**: 1 of 1 candidates below the 80% minimum pass rate" in text
        assert "| gpt/default | 0.333 (1/3) | ❌ |" in text
        assert "<small>exit code 1 · complete, 3 of 3 runs · spent $0.0000</small>" in text
        assert "| gpt/default | 3 | 0.333 |" in text
        assert "## Failures\n2 of 3 runs failed; each lists what went wrong." in text
        assert "  - ❌ **valid** no (needs true)" in text
        assert "place_order" not in text
        assert "  - error: Out of stock" in text
        assert "| ada | gpt/default | 1/2 |" in text
        assert "per tag" not in text
        assert "git" not in text.split("## Run details")[1]
        assert "> ⚠️ gpt/default ran fewer than 5 times" in text

    def test_each_failed_run_shows_the_threshold_its_case_was_checked_against(self, tmp_path):
        cases = [
            EvalCase(id="ada"),
            EvalCase(
                id="bob",
                metrics=[
                    {"type": "mock_called", "name": "orders", "params": {"method": "m"}, "pass_threshold": {"min": 3}}
                ],
            ),
        ]
        runs = [run_result("ada", passed=False, orders=0.0), run_result("bob", passed=False, orders=2.0)]
        report = SuiteReport(
            loaded_suite(tmp_path, cases=cases), SuiteRunResult(suite="o", planned_runs=2, runs=runs, spent_usd=0)
        )
        runs[1].thresholds["orders"] = ThresholdResult(passed=False, required=True)

        [path] = ReportMdWriter().write(report, tmp_path)

        text = path.read_text()
        assert "  - ❌ **orders** 0 (needs ≥ 1)" in text and "  - ❌ **orders** 2 (needs ≥ 3)" in text

    def test_a_failed_run_shows_what_the_judge_said_about_each_criterion(self, tmp_path):
        [path] = ReportMdWriter().write(judged_suite_report(tmp_path, [judged_run(passed=False)]), tmp_path)

        text = path.read_text()
        assert (
            "  - judge says (0.5):\n"
            "    - complete (failure): The XL mug was ordered instead of the regular one.\n"
            "    - no_invented (success): All SKUs exist."
        ) in text
        assert "  - reasoning:" not in text

    def test_a_short_legend_under_the_comparison_explains_every_column(self, tmp_path):
        metrics = [
            {
                "type": "mock_called",
                "name": "orders",
                "description": "orders placed",
                "params": {"method": "m"},
                "pass_threshold": {"min": 1},
            },
            {"type": "json_schema", "name": "valid", "params": {"schema": {}}},
            {
                "type": "tool_called",
                "name": "calls",
                "params": {"name": "t"},
                "pass_threshold": {"max": 2},
                "required": False,
            },
        ]
        [path] = ReportMdWriter().write(suite_report(tmp_path, [run_result("ada")], metrics=metrics), tmp_path)

        comparison = path.read_text().split("## Comparison")[1].split("## ")[0]
        assert "<small>**Pass rate**: runs meeting every pass threshold; needs 80%</small><br>" in comparison
        assert "<small>**orders**: orders placed · avg · pass: ≥ 1</small>" in comparison
        assert (
            "<small>**valid**: Whether the output conforms to a JSON Schema, given inline as 'schema' or as a 'schema_file' · % of runs · pass: true</small>"
            in comparison
        )
        assert (
            "<small>**calls**: How many times the agent called a tool, optionally only with given argument values · avg · warn unless ≤ 2</small>"
            in comparison
        )

    def test_the_failures_legend_lists_only_the_fields_the_report_shows(self, tmp_path):
        [path] = ReportMdWriter().write(suite_report(tmp_path, _flaky_and_failing_runs()), tmp_path)

        failures = path.read_text().split("## Failures")[1].split("\n- **")[0]
        assert (
            "<small>**❌ metric**: a pass threshold the run missed: its value, then what passing needs</small>"
            in failures
        )
        assert "<small>**error**:" in failures
        assert "**missing**" not in failures and "**trace**" not in failures

    def test_a_run_missing_several_thresholds_is_listed_once_with_each(self, tmp_path):
        [path] = ReportMdWriter().write(suite_report(tmp_path, _flaky_and_failing_runs()), tmp_path)

        failures = path.read_text().split("## Failures")[1].split("## ")[0]
        assert failures.count("- **bob**") == 1
        assert "❌ **orders**" in failures and "❌ **valid**" in failures

    def test_a_failed_run_shows_its_case_tags_and_description(self, tmp_path):
        runs = [run_result("ada", passed=False), run_result("bob", passed=False)]

        [path] = ReportMdWriter().write(suite_report(tmp_path, runs), tmp_path)

        text = path.read_text()
        assert "- **ada** (vip) · gpt/default · repeat 1\n  <small>A regular order</small>\n" in text
        assert "- **bob** · gpt/default · repeat 1\n  - ❌" in text

    def test_a_failed_run_links_its_trace_file_instead_of_showing_the_calls(self, tmp_path):
        report = suite_report(tmp_path, _flaky_and_failing_runs(), ["report", "traces"])

        [path] = ReportMdWriter().write(report, tmp_path)

        text = path.read_text()
        assert "  - trace: [runs/bob__gpt__default__r1.json](runs/bob__gpt__default__r1.json) (1 tool calls)" in text
        assert "place_order" not in text
        assert "<small>**trace**: the run's every LLM, tool and mock call, as JSON</small>" in text

    def test_without_a_min_pass_rate_the_report_has_no_verdict(self, tmp_path):
        report = suite_report(tmp_path, [run_result("ada", passed=False)], min_pass_rate=None)

        [path] = ReportMdWriter().write(report, tmp_path)

        text = path.read_text()
        assert "## Verdict" not in text and "needs" not in text.split("## Failures")[0]
        assert "<small>exit code 0 · complete, 1 of 1 runs · spent $0.0000</small>" in text

    def test_an_untracked_budget_has_its_own_verdict_without_the_threshold(self, tmp_path):
        result = SuiteRunResult(
            suite="orders", planned_runs=3, runs=[run_result("ada")], spent_usd=0.1, stopped_reason="budget_untracked"
        )

        [path] = ReportMdWriter().write(SuiteReport(loaded_suite(tmp_path), result), tmp_path)

        text = path.read_text()
        assert "## Verdict\n**⚠️ PARTIAL**: a call could not be priced, so the run stopped after 1 of 3 runs" in text
        assert "minimum pass rate" not in text.split("\n")[3]

    def test_a_run_where_everything_passed_has_no_failures_section(self, tmp_path):
        [path] = ReportMdWriter().write(suite_report(tmp_path, [run_result("ada"), run_result("bob")]), tmp_path)

        text = path.read_text()
        assert "## Verdict\n**✅ PASSED**: every candidate reached the 80% minimum pass rate" in text
        assert "| gpt/default | 1 (2/2) | ✅ |" in text
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
