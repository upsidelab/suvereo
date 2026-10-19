from agent.evaluation.aggregation import PASS_RATE

from .exit_code import ExitCode
from .markdown_text import MarkdownText
from .suite_report import SuiteReport
from .suite_verdict import SuiteVerdict

LOW_SAMPLE_RUNS = 5
HEADLINES = {
    ExitCode.PASSED: "**✅ PASSED**: every candidate reached the {min_pass_rate:.0%} minimum pass rate",
    ExitCode.BELOW_MIN_PASS_RATE: "**❌ FAILED**: {below} of {candidates} candidates below the {min_pass_rate:.0%} minimum "
    "pass rate",
    ExitCode.BUDGET_EXCEEDED: "**⚠️ PARTIAL**: the budget ran out after {runs} of {planned} runs",
    ExitCode.INVALID_SUITE: "**⚠️ INVALID**: the suite is invalid",
    ExitCode.RUNTIME_ERROR: "**⚠️ ERROR**: the run failed",
}
UNTRACKED_BUDGET_HEADLINE = (
    "**⚠️ PARTIAL**: a call could not be priced, so the run stopped after {runs} of {planned} runs"
)


class VerdictSection:
    """The top of report.md: the verdict in one bold line, each candidate's pass rate against the minimum, warnings,
    and the run's exit code, size and spend in small print. Without a min_pass_rate there is no verdict to give, so
    only a budget stop, the warnings and the small print remain."""

    @classmethod
    def render(cls, report: SuiteReport, verdict: SuiteVerdict) -> str:
        min_pass_rate = report.loaded.suite.min_pass_rate
        if min_pass_rate is None:
            headline = [cls._headline(report, verdict)] if verdict.exit_code != ExitCode.PASSED else []
            warnings = [f"> ⚠️ {warning}" for warning in cls._warnings(report)]
            return "\n\n".join([*headline, *warnings, cls._run_line(report, verdict)])
        rows = []
        for c in report.candidates:
            passed = sum(run.passed for run in c.runs)
            rate = c.metrics[PASS_RATE].value
            ok = c.candidate not in verdict.below_min_pass_rate
            rows.append([c.candidate, f"{MarkdownText.cell(rate)} ({passed}/{len(c.runs)})", "✅" if ok else "❌"])
        parts = [
            f"## Verdict\n{cls._headline(report, verdict)}",
            MarkdownText.table(["Candidate", f"Pass rate (needs {min_pass_rate:.0%})", "Result"], rows),
            *(f"> ⚠️ {warning}" for warning in cls._warnings(report)),
            cls._run_line(report, verdict),
        ]
        return "\n\n".join(parts)

    @staticmethod
    def _headline(report: SuiteReport, verdict: SuiteVerdict) -> str:
        result = report.result
        template = HEADLINES[verdict.exit_code]
        if verdict.exit_code == ExitCode.BUDGET_EXCEEDED and result.stopped_reason == "budget_untracked":
            template = UNTRACKED_BUDGET_HEADLINE
        return template.format(
            min_pass_rate=report.loaded.suite.min_pass_rate,
            below=len(verdict.below_min_pass_rate),
            candidates=len(report.candidates),
            runs=len(result.runs),
            planned=result.planned_runs,
        )

    @staticmethod
    def _warnings(report: SuiteReport) -> list[str]:
        warnings = []
        if unpriced := report.result.unpriced_models:
            warnings.append(f"Calls to {', '.join(unpriced)} could not be priced; spend is a minimum.")
        if low := [c.candidate for c in report.candidates if len(c.runs) < LOW_SAMPLE_RUNS]:
            warnings.append(f"{', '.join(low)} ran fewer than {LOW_SAMPLE_RUNS} times; add repeats to trust the rates.")
        return warnings

    @staticmethod
    def _run_line(report: SuiteReport, verdict: SuiteVerdict) -> str:
        result = report.result
        budget = f" of {MarkdownText.usd(result.budget_usd)}" if result.budget_usd else ""
        return (
            f"<small>exit code {int(verdict.exit_code)} · {verdict.status}, {len(result.runs)} of "
            f"{result.planned_runs} runs · spent {MarkdownText.usd(result.spent_usd)}{budget}</small>"
        )
