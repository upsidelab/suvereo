from pathlib import Path

from enthusiast_common.evaluation.metrics.auto import DurationSeconds

from agent.evaluation.aggregation import FLAKY_RATE, PASS_RATE
from agent.evaluation.runner import RunResult

from .base_report_writer import BaseReportWriter
from .markdown_text import MarkdownText
from .suite_report import SuiteReport
from .suite_verdict import SuiteVerdict
from .threshold_text import threshold_text
from .verdict_section import VerdictSection

MAX_TRACE_STEPS = 12


class ReportMdWriter(BaseReportWriter):
    """report.md, for people and coding agents: the verdict, a comparison of the candidates, the diff against a
    baseline run, the failed runs grouped by the pass threshold they missed (with values, errors and a compact trace),
    flaky cases, and how the run was made."""

    NAME = "report"

    def write(self, report: SuiteReport, run_dir: Path) -> list[Path]:
        sections = [
            f"# {report.result.suite or 'Suite'} evaluation",
            VerdictSection.render(report, SuiteVerdict.of(report)),
            self._comparison_section(report),
            self._baseline_diff_section(report),
            self._failures_section(report),
            self._flaky_cases_section(report),
            self._run_details_section(report),
        ]
        path = run_dir / "report.md"
        path.write_text("\n\n".join(section for section in sections if section) + "\n", encoding="utf-8")
        return [path]

    @staticmethod
    def _comparison_section(report: SuiteReport) -> str:
        metrics = list(report.metric_configs)
        header = ["Candidate", "Runs", "Pass rate", "Flaky", *metrics, "Cost / run", "p95 time (s)"]
        rows = []
        for c in report.candidates:
            duration = c.metrics.get(DurationSeconds.NAME)
            rows.append(
                [
                    c.candidate,
                    len(c.runs),
                    MarkdownText.cell(c.metrics[PASS_RATE].value),
                    MarkdownText.cell(c.metrics[FLAKY_RATE].value),
                    *(MarkdownText.cell(c.metrics[m].value) if m in c.metrics else "–" for m in metrics),
                    MarkdownText.usd(c.cost_mean_usd),
                    MarkdownText.cell(duration.p95 if duration else None),
                ]
            )
        return "## Comparison\nBy pass rate, then mean cost.\n\n" + MarkdownText.table(header, rows)

    @staticmethod
    def _baseline_diff_section(report: SuiteReport) -> str:
        diff = report.baseline_diff
        if diff is None:
            return ""
        header = ["Candidate", "Pass rate", *report.metric_configs]
        rows = [
            [
                change.candidate,
                MarkdownText.change(change.pass_rate),
                *(
                    MarkdownText.change(change.metrics[m]) if m in change.metrics else "–"
                    for m in report.metric_configs
                ),
            ]
            for change in diff.candidates
        ]
        lines = [
            f"## Baseline diff\nAgainst {diff.baseline} (started {MarkdownText.cell(diff.baseline_started_at)}).",
            MarkdownText.table(header, rows),
        ]
        for title, case_changes in (("Regressed", diff.regressed), ("Improved", diff.improved)):
            items = ", ".join(f"{c.case_id} ({c.candidate}: {c.before} → {c.after})" for c in case_changes)
            lines.append(f"{title}: {items or 'none'}.")
        return "\n\n".join(lines)

    @classmethod
    def _failures_section(cls, report: SuiteReport) -> str:
        failed = [run for run in report.runs if not run.passed]
        if not failed:
            return ""
        groups: dict[str, list[RunResult]] = {}
        for run in failed:
            names = [name for name, threshold in run.thresholds.items() if not threshold.passed and threshold.required]
            for name in names or ["error" if run.trace.error else "execution failed"]:
                groups.setdefault(name, []).append(run)
        sections = ["## Failures\nFailed runs by the pass threshold they missed, most failures first."]
        for name, runs in sorted(groups.items(), key=lambda item: -len(item[1])):
            heading = f"### {name} — {len(runs)} run(s)"
            sections.append("\n".join([heading, *(cls._failed_run_lines(run, name, report) for run in runs)]))
        return "\n\n".join(sections)

    @staticmethod
    def _failed_run_lines(run: RunResult, name: str, report: SuiteReport) -> str:
        lines = [f"- **{run.case_id}** · {run.candidate} · repeat {run.repeat}"]
        result = run.metrics.get(name)
        if result is not None:
            threshold = threshold_text(report.threshold_for(run.case_id, name))
            needs = f" (pass threshold: {threshold})" if threshold else ""
            lines.append(f"  - value: {MarkdownText.cell(result.value)}{needs}")
            lines += [
                f"  - {key}: {MarkdownText.one_line(value)}"
                for key, value in result.details.items()
                if value not in (None, "", [], {})
            ]
        if run.trace.error:
            lines.append(f"  - error: {MarkdownText.one_line(run.trace.error)}")
        steps = [
            f"{c.name}({MarkdownText.one_line(c.args)}) → {MarkdownText.one_line(c.error or c.output)}"
            for c in run.trace.tool_calls
        ]
        if steps:
            lines.append(
                "  - trace: " + " ⟶ ".join(steps[:MAX_TRACE_STEPS]) + (" …" if len(steps) > MAX_TRACE_STEPS else "")
            )
        if trace := report.linked_trace_path(run):
            lines.append(f"  - full trace: [{trace}]({trace})")
        return "\n".join(lines)

    @staticmethod
    def _flaky_cases_section(report: SuiteReport) -> str:
        rows = [
            [o.case_id, o.candidate, f"{o.passed_runs}/{o.runs}"] for o in report.case_outcomes() if o.status == "flaky"
        ]
        return (
            "## Flaky cases\nPassed on some repeats and failed on others.\n\n"
            + MarkdownText.table(["Case", "Candidate", "Passed"], rows)
            if rows
            else ""
        )

    @staticmethod
    def _run_details_section(report: SuiteReport) -> str:
        result, suite, git = report.result, report.loaded.suite, report.git
        models = (
            ", ".join(f"{m.display_label} ({m.provider} {m.model})" for m in suite.models)
            or "the DataSet's configured model"
        )
        lines = [
            "## Run details",
            f"- started {MarkdownText.cell(result.started_at)}, finished {MarkdownText.cell(result.finished_at)}",
            f"- models: {models}; variants: {', '.join(['default', *(v.name for v in suite.variants)])}; repeats: {suite.repeats}",
            f"- prices as of {result.pricing_as_of or '–'}",
            f"- git: {git.sha or 'not a git checkout'}" + (" (uncommitted changes)" if git.dirty else ""),
        ]
        if report.args:
            lines.append(f"- command: `{' '.join(report.args)}`")
        return "\n".join(lines)
