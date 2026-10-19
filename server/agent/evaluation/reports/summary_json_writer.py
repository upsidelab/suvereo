import json
from pathlib import Path
from typing import Any

from agent.evaluation.aggregation import FIRST_ATTEMPT_PASS_RATE, FLAKY_RATE, PASS_RATE, CandidateMetrics
from agent.evaluation.runner import RunResult

from .base_report_writer import BaseReportWriter
from .suite_report import SuiteReport
from .suite_verdict import SuiteVerdict
from .summary_file import SUMMARY_FILE
from .threshold_text import threshold_text


class SummaryJsonWriter(BaseReportWriter):
    """summary.json, always written (ReportOutput runs it whatever is selected): the compact, machine-readable result
    for scripts, CI and coding agents.

    Holds the verdict (status, exit code), how the run was started, each candidate's rates and metric values, each
    pass threshold's pass rate, each case's status per candidate, the runs that failed with the thresholds they
    missed, the diff against a baseline run (--baseline), and the cost against the budget.
    """

    NAME = "summary"

    def write(self, report: SuiteReport, run_dir: Path) -> list[Path]:
        path = run_dir / SUMMARY_FILE
        path.write_text(json.dumps(self.summary(report), indent=2, default=str), encoding="utf-8")
        return [path]

    def summary(self, report: SuiteReport) -> dict[str, Any]:
        """The summary as a JSON-ready dict."""
        verdict, result = SuiteVerdict.of(report), report.result
        return {
            "status": verdict.status,
            "exit_code": int(verdict.exit_code),
            "suite": result.suite,
            "git": report.git.model_dump(),
            "run": {
                "started_at": result.started_at,
                "finished_at": result.finished_at,
                "args": report.args,
                "pricing_as_of": result.pricing_as_of,
                "planned_runs": result.planned_runs,
                "runs": len(result.runs),
                "stopped_reason": result.stopped_reason,
            },
            "min_pass_rate": report.loaded.suite.min_pass_rate,
            "candidates": [self._candidate_summary(c, report, verdict) for c in report.candidates],
            "thresholds": self._threshold_summaries(report),
            "cases": [{**outcome.model_dump(), "status": outcome.status} for outcome in report.case_outcomes()],
            "failing_runs": [self._failing_run_summary(run, report) for run in report.runs if not run.passed],
            "baseline": report.baseline_diff.model_dump() if report.baseline_diff else None,
            "cost": {
                "spent_usd": result.spent_usd,
                "budget_usd": result.budget_usd,
                "unpriced_models": result.unpriced_models,
            },
        }

    @staticmethod
    def _candidate_summary(candidate: CandidateMetrics, report: SuiteReport, verdict: SuiteVerdict) -> dict[str, Any]:
        rates = {name: candidate.metrics[name].value for name in (PASS_RATE, FIRST_ATTEMPT_PASS_RATE, FLAKY_RATE)}
        return {
            "candidate": candidate.candidate,
            "provider": report.provider_of(candidate.model),
            "model": candidate.model,
            "variant": candidate.variant,
            "runs": len(candidate.runs),
            **rates,
            "below_min_pass_rate": candidate.candidate in verdict.below_min_pass_rate,
            "metrics": {
                name: candidate.metrics[name].value for name in report.metric_configs if name in candidate.metrics
            },
            "cost_mean_usd": candidate.cost_mean_usd,
        }

    @staticmethod
    def _threshold_summaries(report: SuiteReport) -> dict[str, Any]:
        """Per metric with a pass threshold: how many checked runs met it, and the threshold as text (several when
        cases override it)."""
        thresholds: dict[str, Any] = {}
        for name in report.metric_configs:
            checked = [run for run in report.runs if name in run.thresholds]
            if checked:
                passed = sum(run.thresholds[name].passed for run in checked)
                thresholds[name] = {
                    "thresholds": sorted(
                        {threshold_text(report.threshold_for(run.case_id, name)) for run in checked} - {None}
                    ),
                    "passed_runs": passed,
                    "checked_runs": len(checked),
                    "pass_rate": passed / len(checked),
                }
        return thresholds

    @staticmethod
    def _failing_run_summary(run: RunResult, report: SuiteReport) -> dict[str, Any]:
        return {
            "case_id": run.case_id,
            "candidate": run.candidate,
            "repeat": run.repeat,
            "failed_thresholds": [
                name for name, threshold in run.thresholds.items() if not threshold.passed and threshold.required
            ],
            "failed_optional_thresholds": [
                name for name, threshold in run.thresholds.items() if not threshold.passed and not threshold.required
            ],
            "error": run.trace.error,
            "trace_file": report.linked_trace_path(run),
        }
