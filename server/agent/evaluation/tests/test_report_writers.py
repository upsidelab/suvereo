import csv
from datetime import datetime

import pytest
from enthusiast_common.evaluation.loaded_suite import LoadedSuite
from enthusiast_common.evaluation.metrics import MetricResult
from enthusiast_common.evaluation.suite import EvalCase, EvalSuite
from enthusiast_common.evaluation.trace import ExecutionTrace

from agent.evaluation.reports import (
    CasesCsvWriter,
    ComparisonCsvWriter,
    CsvTable,
    MetricsCsvWriter,
    ReportOutput,
    ResultsCsvWriter,
    RunDirectory,
    SuiteReport,
)
from agent.evaluation.runner import GateResult, RunResult
from agent.evaluation.runner.suite_run_result import SuiteRunResult

CASES = [EvalCase(id="ada", tags=["vip"], description="A regular order"), EvalCase(id="bob")]


def _loaded(tmp_path, **changes) -> LoadedSuite:
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
    return LoadedSuite(path=tmp_path / "suite.yaml", suite=suite, cases=CASES)


def _run(case_id, model="gpt", repeat=1, passed=True, cost=0.01, orders=1.0, error=None):
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


def _report(tmp_path, runs, selected=None, **suite_changes) -> SuiteReport:
    result = SuiteRunResult(suite="orders", planned_runs=len(runs), runs=runs, spent_usd=0.0)
    return SuiteReport(_loaded(tmp_path, **suite_changes), result, selected)


def _rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


class TestCsvTable:
    def test_writes_a_bom_and_spreadsheet_friendly_cells(self, tmp_path):
        path = CsvTable.write(tmp_path / "t.csv", ["a", "b", "c", "d"], [[True, None, ["x", "y"], 'say "hi", ok']])

        assert path.read_bytes().startswith(b"\xef\xbb\xbf")
        assert _rows(path) == [{"a": "true", "b": "", "c": "x;y", "d": 'say "hi", ok'}]


class TestResultsCsvWriter:
    def test_one_row_per_run_with_metrics_gates_and_components(self, tmp_path):
        runs = [_run("ada"), _run("bob", passed=False, orders=0.0, error="Boom")]

        [path] = ResultsCsvWriter().write(_report(tmp_path, runs), tmp_path)

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
        assert (bob["passed"], bob["error"], bob["failed_gates"]) == ("false", "Boom", "orders;valid")
        assert ada["trace_file"] == ""

    def test_links_trace_files_only_when_traces_are_written(self, tmp_path):
        [path] = ResultsCsvWriter().write(_report(tmp_path, [_run("ada")], ["results", "traces"]), tmp_path)

        assert _rows(path)[0]["trace_file"] == "runs/ada__gpt__default__r1.json"


class TestSuiteReport:
    def test_run_ids_stay_unique_when_unsafe_characters_are_replaced(self, tmp_path):
        report = _report(tmp_path, [])
        slashed, dashed = _run("ada", model="a/b"), _run("ada", model="a-b")

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
        runs = [_run("ada"), _run("bob")]
        for run, label in zip(runs, ["yes", "yes"]):
            run.metrics["verdict"] = MetricResult(value=label)

        [path] = ComparisonCsvWriter().write(_report(tmp_path, runs, metrics=metrics), tmp_path)

        assert _rows(path)[0]["verdict__distribution"] == "yes:2"

    def test_one_row_per_candidate_by_pass_rate_then_cost(self, tmp_path):
        runs = [
            _run("ada", model="cheap", cost=0.01),
            _run("bob", model="cheap", passed=False, cost=0.01),
            _run("ada", model="pricey", cost=0.05),
            _run("bob", model="pricey", cost=0.05),
            _run("ada", model="also", cost=0.02),
            _run("bob", model="also", cost=0.02),
        ]

        [path] = ComparisonCsvWriter().write(_report(tmp_path, runs), tmp_path)

        rows = _rows(path)
        assert [r["candidate"] for r in rows] == ["also/default", "pricey/default", "cheap/default"]
        assert (rows[2]["pass_rate"], rows[2]["orders__mean"], rows[2]["valid__rate"]) == ("0.5", "1.0", "0.5")
        assert (rows[0]["cost_mean_usd"], rows[0]["duration_p95_s"]) == ("0.02", "2.0")


class TestCasesCsvWriter:
    def test_one_row_per_case_and_candidate_with_how_its_repeats_went(self, tmp_path):
        runs = [
            _run("ada", repeat=1),
            _run("ada", repeat=2, passed=False),
            _run("bob", repeat=1, passed=False),
            _run("bob", repeat=2, passed=False),
        ]

        [path] = CasesCsvWriter().write(_report(tmp_path, runs), tmp_path)

        ada, bob = _rows(path)
        assert (ada["candidate"], ada["status"], ada["passed_runs"], ada["runs"]) == ("gpt/default", "flaky", "1", "2")
        assert (ada["description"], bob["status"]) == ("A regular order", "fail")


class TestMetricsCsvWriter:
    def test_one_row_per_run_metric_and_component_with_its_gate(self, tmp_path):
        [path] = MetricsCsvWriter().write(_report(tmp_path, [_run("ada")]), tmp_path)

        by_metric = {(r["metric"], r["component"]): r for r in _rows(path)}
        assert (by_metric["orders", ""]["passed"], by_metric["orders", ""]["gate"]) == ("true", "min 1.0")
        assert by_metric["valid", ""]["gate"] == "equals true"
        assert by_metric["orders", "precision"]["value"] == "0.5"
        assert by_metric["cost_usd", ""]["gate"] == ""

    def test_list_gates_follow_the_csv_conventions(self, tmp_path):
        metrics = [{"type": "json_schema", "name": "valid", "params": {"schema": {}}, "gate": {"in": [True, "maybe"]}}]

        [path] = MetricsCsvWriter().write(_report(tmp_path, [_run("ada")], metrics=metrics), tmp_path)

        assert {r["metric"]: r["gate"] for r in _rows(path)}["valid"] == "in true;maybe"


class TestReportOutput:
    def test_writes_only_the_selected_reports(self, tmp_path):
        report = _report(tmp_path, [_run("ada")])

        written = ReportOutput().write(report, ["report", "comparison", "traces"], tmp_path)

        assert sorted(p.relative_to(tmp_path).as_posix() for p in written) == [
            "comparison.csv",
            "runs/ada__gpt__default__r1.json",
        ]

    def test_the_suite_selects_reports_unless_the_run_overrides_them(self, tmp_path):
        assert _report(tmp_path, []).reports == ["report", "results"]
        assert _report(tmp_path, [], reports=["cases"]).reports == ["cases"]
        assert _report(tmp_path, [], ["metrics"], reports=["cases"]).reports == ["metrics"]


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
        assert sorted(p.name for p in (tmp_path / "results").iterdir()) == sorted(["latest", run_dir.name])


@pytest.mark.parametrize("reports", [["results", "html"], ["everything"]])
def test_an_unknown_report_name_is_rejected(tmp_path, reports):
    with pytest.raises(ValueError):
        _loaded(tmp_path, reports=reports)
