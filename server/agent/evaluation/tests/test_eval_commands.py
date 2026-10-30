import json
import logging
import sys
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command

from agent.evaluation.reports import ExitCode, SuiteVerdict
from agent.evaluation.suite_evaluation import SuiteEvaluation, SuiteEvaluationOutcome
from agent.evaluation.suite_loader import SuiteLoader

from .suite_reports import loaded_suite, run_result, suite_report


def _run_command(command, *args):
    """Run a command; returns its exit code, stdout and stderr."""
    stdout, stderr = StringIO(), StringIO()
    try:
        call_command(command, *args, stdout=stdout, stderr=stderr)
        code = 0
    except SystemExit as e:
        code = e.code
    return code, stdout.getvalue(), stderr.getvalue()


@pytest.fixture
def suite_file(tmp_path):
    path = tmp_path / "suite.yaml"
    path.write_text("agent: {type: order-intake}")
    return path


def _evaluation_outcome(tmp_path, runs):
    report = suite_report(tmp_path, runs)
    return SuiteEvaluationOutcome(report=report, verdict=SuiteVerdict.of(report), run_dir=tmp_path / "results" / "r1")


class TestRunEval:
    def test_prints_the_comparison_and_exits_with_the_verdicts_code(self, tmp_path, suite_file):
        outcome = _evaluation_outcome(tmp_path, [run_result("ada"), run_result("bob", passed=False)])

        with (
            patch.object(SuiteLoader, "load", return_value=loaded_suite(tmp_path)),
            patch.object(SuiteEvaluation, "run", return_value=outcome),
        ):
            code, stdout, _ = _run_command("runeval", str(suite_file))

        assert code == ExitCode.BELOW_MIN_PASS_RATE
        assert "| gpt/default | 2 | 0.5 |" in stdout
        assert "Run complete, exit code 1" in stdout

    def test_json_format_prints_only_the_summary(self, tmp_path, suite_file):
        outcome = _evaluation_outcome(tmp_path, [run_result("ada")])

        with (
            patch.object(SuiteLoader, "load", return_value=loaded_suite(tmp_path)),
            patch.object(SuiteEvaluation, "run", return_value=outcome),
        ):
            code, stdout, _ = _run_command("runeval", str(suite_file), "--format", "json")

        assert code == ExitCode.PASSED
        assert json.loads(stdout)["exit_code"] == 0

    def test_json_format_sends_logs_written_to_stdout_to_stderr_while_running(self, tmp_path, suite_file):
        handler = logging.StreamHandler(sys.stdout)
        streams = []
        logging.getLogger("httpx").addHandler(handler)
        try:
            with (
                patch.object(SuiteLoader, "load", return_value=loaded_suite(tmp_path)),
                patch.object(
                    SuiteEvaluation,
                    "run",
                    side_effect=lambda: streams.append(handler.stream) or _evaluation_outcome(tmp_path, []),
                ),
            ):
                _run_command("runeval", str(suite_file), "--format", "json")
        finally:
            logging.getLogger("httpx").removeHandler(handler)

        assert streams == [sys.stderr]
        assert handler.stream is sys.stdout

    def test_options_reach_the_selection_and_run_options(self, tmp_path, suite_file):
        with (
            patch.object(SuiteLoader, "load", return_value=loaded_suite(tmp_path)) as load,
            patch.object(SuiteEvaluation, "run", return_value=_evaluation_outcome(tmp_path, [run_result("ada")])),
            patch.object(SuiteEvaluation, "__init__", return_value=None) as evaluation,
        ):
            _run_command(
                "runeval",
                str(suite_file),
                "--case",
                "ada",
                "--tag",
                "vip",
                "--model",
                "gpt",
                "--repeats",
                "2",
                "--parallel",
                "3",
                "--budget",
                "1.5",
                "--reports",
                "report, traces",
                "--note",
                "try it",
            )

        selection = load.call_args.args[1]
        assert (selection.case_ids, selection.tags, selection.models, selection.repeats) == (
            ["ada"],
            ["vip"],
            ["gpt"],
            2,
        )
        _, run_options, reports, baseline, note, command_line = evaluation.call_args.args
        assert (run_options.parallel, run_options.budget_usd) == (3, 1.5)
        assert (reports, baseline, note) == (["report", "traces"], None, "try it")
        assert command_line == [
            "runeval",
            str(suite_file),
            "--model",
            "gpt",
            "--case",
            "ada",
            "--tag",
            "vip",
            "--repeats",
            "2",
            "--budget",
            "1.5",
            "--parallel",
            "3",
            "--reports",
            "report, traces",
            "--note",
            "try it",
        ]

    def test_rerun_failed_selects_the_cases_a_summary_failed(self, tmp_path, suite_file):
        (tmp_path / "old.json").write_text('{"failing_runs": [{"case_id": "bob"}]}')

        with (
            patch.object(SuiteLoader, "load", return_value=loaded_suite(tmp_path)) as load,
            patch.object(SuiteEvaluation, "run", return_value=_evaluation_outcome(tmp_path, [run_result("bob")])),
        ):
            _run_command("runeval", str(suite_file), "--rerun-failed", str(tmp_path / "old.json"))

        assert load.call_args.args[1].case_ids == ["bob"]

    @pytest.mark.parametrize(
        "options, message",
        [
            (["--reports", "report,pdf"], "Invalid option"),
            (["--rerun-failed", "missing.json"], "Cannot read the summary"),
            (["--parallel", "0"], "Invalid option"),
        ],
    )
    def test_an_invalid_option_exits_as_an_invalid_suite(self, suite_file, options, message):
        code, _, stderr = _run_command("runeval", str(suite_file), *options)

        assert code == ExitCode.INVALID_SUITE
        assert message in stderr

    def test_an_invalid_suite_exits_with_2(self, tmp_path):
        code, _, stderr = _run_command("runeval", str(tmp_path / "missing.yaml"))

        assert code == ExitCode.INVALID_SUITE
        assert "cannot read the suite" in stderr

    def test_an_error_while_running_exits_with_4(self, tmp_path, suite_file):
        with (
            patch.object(SuiteLoader, "load", return_value=loaded_suite(tmp_path)),
            patch.object(SuiteEvaluation, "run", side_effect=RuntimeError("database gone")),
        ):
            code, _, stderr = _run_command("runeval", str(suite_file))

        assert code == ExitCode.RUNTIME_ERROR
        assert "RuntimeError: database gone" in stderr

    def test_history_prints_the_recorded_runs(self, tmp_path, suite_file):
        (tmp_path / "results").mkdir()
        (tmp_path / "results" / "history.jsonl").write_text(
            '{"run": "r1", "candidate": "gpt/default", "pass_rate": 0.5, "note": "first"}\n'
        )

        code, stdout, _ = _run_command("runeval", str(suite_file), "--history")

        assert code == 0
        assert "| r1 | gpt/default | 0.5 | – | – | – | first |" in stdout


class TestValidateEval:
    def test_reports_the_planned_runs_of_a_valid_suite(self, tmp_path, suite_file):
        loaded = loaded_suite(tmp_path, variants=[{"name": "v2", "agent_config": {"x": 1}}], repeats=3)

        with patch.object(SuiteLoader, "load", return_value=loaded):
            code, stdout, _ = _run_command("validateeval", str(suite_file))

        assert code == 0
        assert "2 case(s), 12 planned run(s)" in stdout

    def test_an_invalid_suite_exits_with_2(self, tmp_path):
        code, _, stderr = _run_command("validateeval", str(tmp_path / "missing.yaml"))

        assert code == ExitCode.INVALID_SUITE
        assert "cannot read the suite" in stderr


class TestEvalSchemaAndMetrics:
    def test_evalschema_prints_the_suite_json_schema(self):
        _, stdout, _ = _run_command("evalschema")

        assert {"agent", "metrics", "cases"} <= set(json.loads(stdout)["required"])

    def test_listevalmetrics_lists_each_builtin_with_its_params(self):
        _, stdout, _ = _run_command("listevalmetrics")

        assert "cost_usd: number (measured on every run)" in stdout
        assert "attempts: number (measured on every execution run)" in stdout
        assert "turns: number (measured on every conversation run)" in stdout
        assert "path (required)" in stdout
