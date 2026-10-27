import csv
import json
from datetime import datetime

import pytest
from enthusiast_common.evaluation.metrics import MetricResult
from enthusiast_common.evaluation.suite import ConversationEvalCase

from agent.evaluation.reports import (
    CasesCsvWriter,
    ComparisonCsvWriter,
    CsvTable,
    MetricsCsvWriter,
    ReportOutput,
    ResultsCsvWriter,
    RunDirectory,
    TraceFilesWriter,
    TranscriptsWriter,
)

from .suite_reports import (
    conversation_run,
    conversation_suite_report,
    judged_run,
    judged_suite_report,
    loaded_suite,
    run_result,
    suite_report,
)


def _rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


class TestCsvTable:
    def test_writes_a_bom_and_spreadsheet_friendly_cells(self, tmp_path):
        path = CsvTable.write(tmp_path / "t.csv", ["a", "b", "c", "d"], [[True, None, ["x", "y"], 'say "hi", ok']])

        assert path.read_bytes().startswith(b"\xef\xbb\xbf")
        assert _rows(path) == [{"a": "true", "b": "", "c": "x;y", "d": 'say "hi", ok'}]


class TestResultsCsvWriter:
    def test_one_row_per_run_with_metrics_thresholds_and_components(self, tmp_path):
        runs = [run_result("ada"), run_result("bob", passed=False, orders=0.0, error="Boom")]

        [path] = ResultsCsvWriter().write(suite_report(tmp_path, runs), tmp_path)

        ada, bob = _rows(path)
        assert (ada["run_id"], ada["tags"], ada["provider"], ada["candidate"]) == (
            "ada__gpt__default__r1",
            "vip",
            "OpenAI",
            "gpt/default",
        )
        assert (ada["orders"], ada["orders__passed"], ada["orders.precision"], ada["valid"]) == (
            "1.0",
            "true",
            "0.5",
            "true",
        )
        assert (bob["passed"], bob["error"], bob["failed_thresholds"]) == ("false", "Boom", "orders;valid")
        assert ada["trace_file"] == ""

    def test_a_conversation_suite_shows_its_own_outcome_columns(self, tmp_path):
        conversation = run_result("ada")
        conversation.metrics |= {
            "conversation_completed": MetricResult(value=False),
            "conversation_end": MetricResult(value="gave_up"),
            "goal_reached": MetricResult(value=False),
            "turns": MetricResult(value=3.0),
        }

        [path] = ResultsCsvWriter().write(suite_report(tmp_path, [conversation], kind="conversation"), tmp_path)

        [ada] = _rows(path)
        assert (ada["conversation_completed"], ada["conversation_end"], ada["goal_reached"], ada["turns"]) == (
            "false",
            "gave_up",
            "false",
            "3.0",
        )
        assert "attempts" not in ada and "execution_succeeded" not in ada

    def test_links_trace_files_only_when_traces_are_written(self, tmp_path):
        [path] = ResultsCsvWriter().write(suite_report(tmp_path, [run_result("ada")], ["results", "traces"]), tmp_path)

        assert _rows(path)[0]["trace_file"] == "runs/ada__gpt__default__r1.json"

    def test_a_judge_metric_gets_a_column_with_its_reasoning_per_criterion(self, tmp_path):
        [path] = ResultsCsvWriter().write(judged_suite_report(tmp_path, [judged_run(), run_result("bob")]), tmp_path)

        ada, bob = _rows(path)
        assert ada["judge.reasoning"] == (
            "complete (failure): The XL mug was ordered instead of the regular one. | no_invented (success): All SKUs exist."
        )
        assert bob["judge.reasoning"] == ""
        assert (ada["judge.complete"], ada["judge.no_invented"]) == ("failure", "success")
        assert "orders.reasoning" not in ada


class TestSuiteReport:
    def test_run_ids_stay_unique_when_unsafe_characters_are_replaced(self, tmp_path):
        report = suite_report(tmp_path, [])
        slashed, dashed = run_result("ada", model="a/b"), run_result("ada", model="a-b")

        assert report.run_id(dashed) == "ada__a-b__default__r1"
        assert report.run_id(slashed).startswith("ada__a-b__default__r1-")
        assert report.run_id(slashed) != report.run_id(dashed)


class TestComparisonCsvWriter:
    def test_a_distribution_metric_lists_every_label_with_its_count(self, tmp_path):
        metrics = [
            {
                "type": "llm_classify",
                "name": "verdict",
                "aggregate": "distribution",
                "params": {"question": "q", "labels": ["yes", "no"], "judge": {"provider": "OpenAI", "model": "m"}},
            }
        ]
        runs = [run_result("ada"), run_result("bob")]
        for run, label in zip(runs, ["yes", "yes"]):
            run.metrics["verdict"] = MetricResult(value=label)

        [path] = ComparisonCsvWriter().write(suite_report(tmp_path, runs, metrics=metrics), tmp_path)

        assert _rows(path)[0]["verdict__distribution"] == "yes:2"

    def test_one_row_per_candidate_by_pass_rate_then_cost(self, tmp_path):
        runs = [
            run_result("ada", model="cheap", cost=0.01),
            run_result("bob", model="cheap", passed=False, cost=0.01),
            run_result("ada", model="pricey", cost=0.05),
            run_result("bob", model="pricey", cost=0.05),
            run_result("ada", model="also", cost=0.02),
            run_result("bob", model="also", cost=0.02),
        ]

        [path] = ComparisonCsvWriter().write(suite_report(tmp_path, runs), tmp_path)

        rows = _rows(path)
        assert [r["candidate"] for r in rows] == ["also/default", "pricey/default", "cheap/default"]
        assert (rows[2]["pass_rate"], rows[2]["orders__mean"], rows[2]["valid__rate"]) == ("0.5", "1.0", "0.5")
        assert (rows[0]["cost_mean_usd"], rows[0]["duration_p95_s"]) == ("0.02", "2.0")
        assert "user_cost_total_usd" not in rows[0]

    def test_a_conversation_suite_has_its_own_rates_and_outcome_figures(self, tmp_path):
        runs = [conversation_run("ada", passed=True), conversation_run("bob")]

        [path] = ComparisonCsvWriter().write(conversation_suite_report(tmp_path, runs), tmp_path)

        [row] = _rows(path)
        assert "first_attempt_pass_rate" not in row
        assert (row["pass_rate"], row["goal_reached__rate"], row["turns__mean"]) == ("0.5", "0.5", "3.0")

    def test_a_conversation_suite_totals_what_its_simulated_users_cost(self, tmp_path):
        runs = [run_result("ada"), run_result("bob")]
        for run in runs:
            run.metrics["user_cost_usd"] = MetricResult(value=0.03)

        [path] = ComparisonCsvWriter().write(suite_report(tmp_path, runs, kind="conversation"), tmp_path)

        [row] = _rows(path)
        assert (row["judge_cost_total_usd"], row["user_cost_total_usd"]) == ("0.0", "0.06")


class TestCasesCsvWriter:
    def test_one_row_per_case_and_candidate_with_how_its_repeats_went(self, tmp_path):
        runs = [
            run_result("ada", repeat=1),
            run_result("ada", repeat=2, passed=False),
            run_result("bob", repeat=1, passed=False),
            run_result("bob", repeat=2, passed=False),
        ]

        [path] = CasesCsvWriter().write(suite_report(tmp_path, runs), tmp_path)

        ada, bob = _rows(path)
        assert (ada["candidate"], ada["status"], ada["passed_runs"], ada["runs"]) == ("gpt/default", "flaky", "1", "2")
        assert (ada["description"], bob["status"]) == ("A regular order", "fail")


class TestMetricsCsvWriter:
    def test_one_row_per_run_metric_and_component_with_its_threshold(self, tmp_path):
        [path] = MetricsCsvWriter().write(suite_report(tmp_path, [run_result("ada")]), tmp_path)

        by_metric = {(r["metric"], r["component"]): r for r in _rows(path)}
        assert (by_metric["orders", ""]["passed"], by_metric["orders", ""]["pass_threshold"]) == ("true", "min 1.0")
        assert by_metric["valid", ""]["pass_threshold"] == "equals true"
        assert by_metric["orders", "precision"]["value"] == "0.5"
        assert by_metric["cost_usd", ""]["pass_threshold"] == ""
        assert by_metric["cost_usd", ""]["details"] == ""

    def test_a_metric_row_holds_its_details_as_json(self, tmp_path):
        [path] = MetricsCsvWriter().write(judged_suite_report(tmp_path, [judged_run()]), tmp_path)

        by_metric = {(r["metric"], r["component"]): r for r in _rows(path)}
        assert json.loads(by_metric["judge", ""]["details"])["reasoning"]["no_invented"] == "All SKUs exist."
        assert by_metric["judge", "complete"]["details"] == ""

    def test_list_thresholds_follow_the_csv_conventions(self, tmp_path):
        metrics = [
            {
                "type": "json_schema",
                "name": "valid",
                "params": {"schema": {}},
                "pass_threshold": {"in": [True, "maybe"]},
            }
        ]

        [path] = MetricsCsvWriter().write(suite_report(tmp_path, [run_result("ada")], metrics=metrics), tmp_path)

        assert {r["metric"]: r["pass_threshold"] for r in _rows(path)}["valid"] == "in true;maybe"


class TestTraceFilesWriter:
    def test_each_trace_file_holds_the_runs_metrics_thresholds_and_trace(self, tmp_path):
        failed = judged_run(passed=False)
        failed.trace.error = "Out of stock"

        [path] = TraceFilesWriter().write(judged_suite_report(tmp_path, [failed]), tmp_path)

        content = json.loads(path.read_text())
        assert path.name == "ada__gpt__default__r1.json"
        assert content["passed"] is False
        assert content["metrics"]["judge"]["details"]["reasoning"]["no_invented"] == "All SKUs exist."
        assert content["thresholds"]["orders"] == {"passed": False, "required": True}
        assert content["error"] == "Out of stock"


class TestReportOutput:
    def test_writes_summary_json_and_the_selected_reports(self, tmp_path):
        report = suite_report(tmp_path, [run_result("ada")])

        written = ReportOutput().write(report, ["report", "comparison", "traces"], tmp_path)

        assert sorted(p.relative_to(tmp_path).as_posix() for p in written) == [
            "comparison.csv",
            "report.md",
            "runs/ada__gpt__default__r1.json",
            "summary.json",
        ]

    def test_summary_json_is_written_even_when_nothing_is_selected(self, tmp_path):
        written = ReportOutput().write(suite_report(tmp_path, [run_result("ada")]), [], tmp_path)

        assert [p.name for p in written] == ["summary.json"]

    def test_the_suite_selects_reports_unless_the_run_overrides_them(self, tmp_path):
        assert suite_report(tmp_path, []).reports == ["report", "results"]
        assert suite_report(tmp_path, [], reports=["cases"]).reports == ["cases"]
        assert suite_report(tmp_path, [], ["metrics"], reports=["cases"]).reports == ["metrics"]


class TestTranscriptsWriter:
    def test_writes_each_conversation_as_a_readable_dialogue(self, tmp_path):
        run = conversation_run(answers=("## Sizes\n- small\n- large",))
        raised = {"answer": None, "error": "RuntimeError: down", "tool_call_run_ids": []}
        run.trace.turns.append(run.trace.turns[0].model_copy(update=raised))
        report = conversation_suite_report(tmp_path, [run], ["transcripts", "traces"])

        [path] = TranscriptsWriter().write(report, tmp_path)

        text = path.read_text()
        assert path.relative_to(tmp_path).as_posix() == "transcripts/ada__gpt__default__r1.md"
        assert text.startswith("# ada · gpt/default · repeat 1\n- passed: no\n- ended: gave_up after 2 turn(s)\n")
        assert '- goal: Order a mug\n- persona: terse\n- facts: {"size": "large"}\n' in text
        assert "- trace: [runs/ada__gpt__default__r1.json](../runs/ada__gpt__default__r1.json)" in text
        assert "## Turn 1\n\n**User**\n\n> message 1\n\n<small>tools called: find_mug (raised)</small>" in text
        assert "**Agent**\n\n> ## Sizes\n> - small\n> - large" in text
        assert "## Turn 2\n\n**User**\n\n> message 1\n\n**Agent raised**\n\n> RuntimeError: down" in text

    def test_a_goal_written_over_several_lines_stays_in_the_header(self, tmp_path):
        case = ConversationEvalCase(id="ada", simulated_user={"goal": "Order a mug\nin large"})
        report = suite_report(tmp_path, [conversation_run()], ["transcripts"], cases=[case], kind="conversation")

        [path] = TranscriptsWriter().write(report, tmp_path)

        assert "- goal: Order a mug in large\n" in path.read_text()

    def test_an_execution_suite_has_no_transcripts(self, tmp_path):
        assert TranscriptsWriter().write(suite_report(tmp_path, [run_result("ada")], ["transcripts"]), tmp_path) == []


class TestRunDirectory:
    def test_creates_a_dated_directory_and_points_latest_at_the_newest(self, tmp_path):
        first = RunDirectory.create(tmp_path, datetime(2026, 10, 14, 9, 30))
        second = RunDirectory.create(tmp_path, datetime(2026, 10, 14, 10, 0))

        assert first.name.startswith("20261014-093000-") and second.is_dir()
        assert (tmp_path / "results" / "latest").resolve() == second.resolve()

    def test_a_latest_that_cannot_be_replaced_leaves_no_stray_link(self, tmp_path):
        (tmp_path / "results" / "latest").mkdir(parents=True)
        (tmp_path / "results" / "latest" / "keep").write_text("x")

        run_dir = RunDirectory.create(tmp_path)

        assert run_dir.is_dir()
        assert sorted(p.name for p in (tmp_path / "results").iterdir()) == sorted(
            [".gitignore", "latest", run_dir.name]
        )


@pytest.mark.parametrize("reports", [["results", "html"], ["everything"]])
def test_an_unknown_report_name_is_rejected(tmp_path, reports):
    with pytest.raises(ValueError):
        loaded_suite(tmp_path, reports=reports)
