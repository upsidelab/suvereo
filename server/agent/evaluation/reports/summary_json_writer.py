import json
from pathlib import Path
from typing import Any

from enthusiast_common.evaluation.metrics.auto import CostUsd

from agent.evaluation.aggregation import FIRST_ATTEMPT_PASS_RATE, FLAKY_RATE, PASS_RATE, CandidateMetrics
from agent.evaluation.runner import RunResult

from .base_report_writer import BaseReportWriter
from .gate_text import gate_text
from .suite_report import SuiteReport
from .suite_verdict import SuiteVerdict

SUMMARY_FILE = "summary.json"


class SummaryJsonWriter(BaseReportWriter):
    """summary.json, always written (ReportOutput runs it whatever is selected): the compact, machine-readable result
    for scripts, CI and coding agents.

    Holds the verdict (status, exit code), how the run was started, each candidate's rates and metric values, each
    gate's pass rate, the runs that failed with their failed gates, and the cost against the budget.
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
            "pass_threshold": report.loaded.suite.pass_threshold,
            "candidates": [self._candidate_summary(c, report, verdict) for c in report.candidates],
            "gates": self._gate_summaries(report),
            "failing_runs": [self._failing_run_summary(run, report) for run in report.runs if not run.passed],
            "cost": {
                "spent_usd": result.spent_usd,
                "budget_usd": result.budget_usd,
                "unpriced_models": result.unpriced_models,
            },
        }

    @staticmethod
    def _candidate_summary(candidate: CandidateMetrics, report: SuiteReport, verdict: SuiteVerdict) -> dict[str, Any]:
        rates = {name: candidate.metrics[name].value for name in (PASS_RATE, FIRST_ATTEMPT_PASS_RATE, FLAKY_RATE)}
        cost = candidate.metrics.get(CostUsd.NAME)
        return {
            "candidate": candidate.candidate,
            "provider": report.provider_of(candidate.model),
            "model": candidate.model,
            "variant": candidate.variant,
            "runs": len(candidate.runs),
            **rates,
            "below_threshold": candidate.candidate in verdict.below_threshold,
            "metrics": {
                name: candidate.metrics[name].value for name in report.metric_configs if name in candidate.metrics
            },
            "cost_mean_usd": cost.mean if cost else None,
        }

    @staticmethod
    def _gate_summaries(report: SuiteReport) -> dict[str, Any]:
        """Per gated metric: how many of the runs it gated passed, and its gates as text (several when cases override
        the gate)."""
        gates: dict[str, Any] = {}
        for name in report.metric_configs:
            gated = [run for run in report.runs if name in run.gates]
            if gated:
                passed = sum(run.gates[name].passed for run in gated)
                gates[name] = {
                    "gates": sorted({gate_text(report.gate_for(run.case_id, name)) for run in gated} - {None}),
                    "passed_runs": passed,
                    "gated_runs": len(gated),
                    "pass_rate": passed / len(gated),
                }
        return gates

    @staticmethod
    def _failing_run_summary(run: RunResult, report: SuiteReport) -> dict[str, Any]:
        return {
            "case_id": run.case_id,
            "candidate": run.candidate,
            "repeat": run.repeat,
            "failed_gates": [name for name, gate in run.gates.items() if not gate.passed and gate.required],
            "failed_optional_gates": [
                name for name, gate in run.gates.items() if not gate.passed and not gate.required
            ],
            "error": run.trace.error,
            "trace_file": report.linked_trace_path(run),
        }
