import json
from unittest.mock import patch

import pytest

from agent.evaluation.reports import ExitCode, ReportOutput, RunHistory, SummaryFile
from agent.evaluation.runner import SuiteRunner
from agent.evaluation.runner.suite_run_result import SuiteRunResult
from agent.evaluation.suite_evaluation import ReportWritingError, SuiteEvaluation

from .suite_reports import loaded_suite, run_result


def _evaluate(tmp_path, runs, **kwargs):
    result = SuiteRunResult(suite="orders", planned_runs=len(runs), runs=runs, spent_usd=0.02)
    with patch.object(SuiteRunner, "run", return_value=result):
        return SuiteEvaluation(loaded_suite(tmp_path), **kwargs).run()


class TestSuiteEvaluation:
    def test_writes_the_selected_reports_and_records_the_run_in_the_history(self, tmp_path):
        outcome = _evaluate(tmp_path, [run_result("ada"), run_result("bob")], reports=["report"], note="first")

        assert outcome.verdict.exit_code == ExitCode.PASSED
        assert outcome.run_dir.parent == tmp_path / "results"
        assert sorted(path.name for path in outcome.run_dir.iterdir()) == ["report.md", "summary.json"]
        assert (tmp_path / "results" / ".gitignore").read_text() == "*\n"
        [entry] = RunHistory(tmp_path).entries()
        assert (entry["run"], entry["note"], entry["exit_code"]) == (outcome.run_dir.name, "first", 0)

    def test_a_baseline_is_diffed_into_the_summary(self, tmp_path):
        first = _evaluate(tmp_path, [run_result("ada"), run_result("bob")])
        baseline = SummaryFile.load("latest", tmp_path)

        second = _evaluate(tmp_path, [run_result("ada"), run_result("bob", passed=False)], baseline=baseline)

        summary = json.loads((second.run_dir / "summary.json").read_text())
        assert summary["baseline"]["baseline"] == str((first.run_dir / "summary.json").resolve())
        assert [c["case_id"] for c in summary["baseline"]["regressed"]] == ["bob"]
        assert second.verdict.exit_code == ExitCode.BELOW_MIN_PASS_RATE

    def test_when_the_reports_fail_the_raw_results_are_kept(self, tmp_path):
        with patch.object(ReportOutput, "write", side_effect=OSError("disk full")):
            with pytest.raises(ReportWritingError, match="raw run results") as raised:
                _evaluate(tmp_path, [run_result("ada")])

        [run_dir] = [path for path in (tmp_path / "results").iterdir() if path.is_dir() and not path.is_symlink()]
        assert str(run_dir / "run_result.json") in str(raised.value)
        assert json.loads((run_dir / "run_result.json").read_text())["runs"][0]["case_id"] == "ada"
