import json

import pytest
from suvereo_common.evaluation.errors import EvalSuiteError

from agent.evaluation.reports import ReportMdWriter, RunHistory, SummaryFile, SummaryJsonWriter
from agent.evaluation.reports.case_outcome import CaseOutcome

from .suite_reports import run_result, suite_report


def _baseline(tmp_path, runs) -> SummaryFile:
    """A summary.json of an earlier run of the same suite, as --baseline reads it."""
    run_dir = tmp_path / "results" / "earlier"
    run_dir.mkdir(parents=True)
    SummaryJsonWriter().write(suite_report(tmp_path, runs), run_dir)
    return SummaryFile.load(str(run_dir), tmp_path)


class TestCaseOutcome:
    @pytest.mark.parametrize("passed_runs, status", [(3, "pass"), (0, "fail"), (1, "flaky")])
    def test_status_follows_how_many_repeats_passed(self, passed_runs, status):
        assert CaseOutcome(case_id="ada", candidate="gpt/default", passed_runs=passed_runs, runs=3).status == status


class TestSummaryFile:
    def test_latest_reads_the_newest_runs_summary(self, tmp_path):
        run_dir = tmp_path / "results" / "20261015-120000-abc"
        run_dir.mkdir(parents=True)
        (run_dir / "summary.json").write_text('{"failing_runs": [{"case_id": "bob"}, {"case_id": "bob"}]}')
        (tmp_path / "results" / "latest").symlink_to(run_dir.name)

        summary = SummaryFile.load("latest", tmp_path)

        assert summary.failing_case_ids() == ["bob"]

    def test_a_file_not_shaped_like_a_summary_fails_before_the_run(self, tmp_path):
        (tmp_path / "other.json").write_text('{"cases": [{"case_id": "ada", "candidate": "x", "status": "passed"}]}')

        with pytest.raises(EvalSuiteError, match="is not a summary.json"):
            SummaryFile.load(str(tmp_path / "other.json"), tmp_path)

    def test_a_missing_summary_is_a_suite_error(self, tmp_path):
        with pytest.raises(EvalSuiteError, match="Cannot read the summary"):
            SummaryFile.load(str(tmp_path / "nowhere.json"), tmp_path)


class TestBaselineDiff:
    def test_lists_cases_that_regressed_and_improved_with_the_pass_rate_change(self, tmp_path):
        baseline = _baseline(tmp_path, [run_result("ada"), run_result("bob", passed=False)])

        report = suite_report(tmp_path, [run_result("ada", passed=False), run_result("bob")], baseline=baseline)

        diff = report.baseline_diff
        assert [(c.case_id, c.before, c.after) for c in diff.regressed] == [("ada", "pass", "fail")]
        assert [(c.case_id, c.before, c.after) for c in diff.improved] == [("bob", "fail", "pass")]
        [change] = diff.candidates
        assert (change.pass_rate.before, change.pass_rate.after, change.pass_rate.delta) == (0.5, 0.5, 0.0)

    def test_number_metrics_get_a_delta_and_other_values_only_before_and_after(self, tmp_path):
        baseline = _baseline(tmp_path, [run_result("ada", orders=1.0)])

        report = suite_report(tmp_path, [run_result("ada", orders=3.0, passed=False)], baseline=baseline)

        metrics = report.baseline_diff.candidates[0].metrics
        assert (metrics["orders"].before, metrics["orders"].after, metrics["orders"].delta) == (1.0, 3.0, 2.0)
        assert (metrics["valid"].before, metrics["valid"].after, metrics["valid"].delta) == (1.0, 0.0, -1.0)

    def test_a_candidate_the_baseline_didnt_run_has_nothing_before(self, tmp_path):
        baseline = _baseline(tmp_path, [run_result("ada", model="other")])

        report = suite_report(tmp_path, [run_result("ada")], baseline=baseline)

        assert report.baseline_diff.candidates[0].pass_rate.before is None
        assert report.baseline_diff.regressed == report.baseline_diff.improved == []

    def test_is_written_to_summary_json_and_report_md(self, tmp_path):
        baseline = _baseline(tmp_path, [run_result("ada")])
        report = suite_report(tmp_path, [run_result("ada", passed=False)], baseline=baseline)

        [summary_path] = SummaryJsonWriter().write(report, tmp_path)
        [report_path] = ReportMdWriter().write(report, tmp_path)

        summary = json.loads(summary_path.read_text())
        assert summary["baseline"]["regressed"] == [
            {"case_id": "ada", "candidate": "gpt/default", "before": "pass", "after": "fail"}
        ]
        assert summary["cases"][0]["status"] == "fail"
        markdown = report_path.read_text()
        assert "## Baseline diff" in markdown
        assert "1 → 0 (-1)" in markdown
        assert "Regressed: ada (gpt/default: pass → fail)." in markdown

    def test_without_a_baseline_there_is_no_diff(self, tmp_path):
        report = suite_report(tmp_path, [run_result("ada")])

        [path] = ReportMdWriter().write(report, tmp_path)

        assert report.baseline_diff is None
        assert "Baseline diff" not in path.read_text()


class TestRunHistory:
    def test_records_a_line_per_candidate_with_the_note(self, tmp_path):
        report = suite_report(tmp_path, [run_result("ada"), run_result("ada", model="other", passed=False)])
        history = RunHistory(tmp_path)

        history.record(report, tmp_path / "20261015-120000-abc", note="shorter prompt")

        entries = history.entries()
        assert [(e["candidate"], e["pass_rate"], e["note"]) for e in entries] == [
            ("gpt/default", 1.0, "shorter prompt"),
            ("other/default", 0.0, "shorter prompt"),
        ]
        assert entries[0]["run"] == "20261015-120000-abc"

    def test_a_variants_prompt_file_is_hashed_so_edits_to_it_show(self, tmp_path):
        (tmp_path / "v2.txt").write_text("Be brief.")
        run = run_result("ada")
        run.variant = "v2"
        report = suite_report(tmp_path, [run], variants=[{"name": "v2", "system_prompt_file": "v2.txt"}])

        RunHistory(tmp_path).record(report, tmp_path / "run")

        [entry] = RunHistory(tmp_path).entries()
        assert len(entry["prompt_hash"]) == 12

    def test_skips_lines_that_are_not_json(self, tmp_path):
        (tmp_path / "results").mkdir()
        (tmp_path / "results" / "history.jsonl").write_text('{"run": "a"}\n{"run": \n')

        assert RunHistory(tmp_path).entries() == [{"run": "a"}]
