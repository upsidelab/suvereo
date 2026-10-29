from pathlib import Path

from enthusiast_common.evaluation.metrics.auto import DurationSeconds
from enthusiast_common.evaluation.suite import SuiteKind

from agent.evaluation.aggregation import FLAKY_RATE, PASS_RATE
from agent.evaluation.runner import RunResult

from .base_report_writer import BaseReportWriter
from .judge_reasoning import REASONING, JudgeReasoning
from .markdown_text import MarkdownText
from .suite_report import SuiteReport
from .suite_verdict import SuiteVerdict
from .threshold_text import threshold_words
from .transcript_markdown import TranscriptMarkdown
from .value_legend import ValueLegend
from .verdict_section import VerdictSection

EMPTY = (None, "", [], {})


class ReportMdWriter(BaseReportWriter):
    """report.md, for people and coding agents: the verdict, a comparison of the candidates, the diff against a
    baseline run, each failed run with the pass thresholds it missed (values, the judge's reasoning, errors, a
    conversation's ending and last turns, and links to the trace and transcript), flaky cases, and how the run was
    made."""

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
        figures = report.outcome_figures
        header = ["Candidate", "Runs", "Pass rate", "Flaky", *figures, *metrics, "Cost / run", "p95 time (s)"]
        rows = []
        for c in report.candidates:
            duration = c.metrics.get(DurationSeconds.NAME)
            rows.append(
                [
                    c.candidate,
                    len(c.runs),
                    MarkdownText.cell(c.metrics[PASS_RATE].value),
                    MarkdownText.cell(c.metrics[FLAKY_RATE].value),
                    *(MarkdownText.cell(c.metrics[f].value) if f in c.metrics else "–" for f in figures),
                    *(MarkdownText.cell(c.metrics[m].value) if m in c.metrics else "–" for m in metrics),
                    MarkdownText.usd(c.cost_mean_usd),
                    MarkdownText.cell(duration.p95 if duration else None),
                ]
            )
        return "\n\n".join(
            [
                "## Comparison\nBy pass rate, then mean cost.",
                MarkdownText.table(header, rows),
                ValueLegend.comparison_note(report),
            ]
        )

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
        sections = [f"## Failures\n{len(failed)} of {len(report.runs)} runs failed; each lists what went wrong."]
        if note := ValueLegend.failures_note(cls._failure_fields(report)):
            sections.append(note)
        sections += [cls._failed_run_lines(run, report) for run in failed]
        return "\n\n".join(sections)

    @staticmethod
    def _missed(run: RunResult) -> list[str]:
        return [name for name, threshold in run.thresholds.items() if not threshold.passed and threshold.required]

    @classmethod
    def _failure_fields(cls, report: SuiteReport) -> list[str]:
        """The fields the failures section lists, in order of first appearance."""
        fields: dict[str, None] = {}
        for run in (run for run in report.runs if not run.passed):
            for name in cls._missed(run):
                if result := run.metrics.get(name):
                    fields |= dict.fromkeys(["missed", *(k for k, v in result.details.items() if v not in EMPTY)])
            fields |= dict.fromkeys(f"{name} says" for name, r in run.metrics.items() if JudgeReasoning.lines(r))
            fields |= dict.fromkeys(["error"] if run.trace.error else [])
            fields |= dict.fromkeys(["ended"] if report.kind == SuiteKind.CONVERSATION else [])
            fields |= dict.fromkeys(["last turns"] if report.kind == SuiteKind.CONVERSATION and run.trace.turns else [])
            fields |= dict.fromkeys(["transcript"] if report.linked_transcript_path(run) else [])
            fields |= dict.fromkeys(["trace"] if report.linked_trace_path(run) else [])
        return [field for field in fields if field != REASONING]

    @classmethod
    def _failed_run_lines(cls, run: RunResult, report: SuiteReport) -> str:
        case = next((c for c in report.cases if c.id == run.case_id), None)
        tags = f" ({', '.join(case.tags)})" if case and case.tags else ""
        lines = [f"- **{run.case_id}**{tags} · {run.candidate} · repeat {run.repeat}"]
        if case and case.description:
            lines.append(f"  <small>{case.description}</small>")
        for name in cls._missed(run):
            lines += cls._missed_lines(run, name, report)
        if not cls._missed(run) and not run.trace.error:
            lines.append("  - ❌ the run failed")
        for judged, judged_result in run.metrics.items():
            if reasons := JudgeReasoning.lines(judged_result):
                lines.append(f"  - {judged} says ({MarkdownText.cell(judged_result.value)}):")
                lines += [f"    - {reason}" for reason in reasons]
        if run.trace.error:
            lines.append(f"  - error: {MarkdownText.one_line(run.trace.error)}")
        if report.kind == SuiteKind.CONVERSATION:
            lines.append(f"  - ended: {TranscriptMarkdown.ending(run.trace)}")
            if last_turns := TranscriptMarkdown.last_turns(run.trace):
                lines += ["  - last turns:", *(f"    - {line}" for line in last_turns)]
        if transcript := report.linked_transcript_path(run):
            lines.append(f"  - transcript: [{transcript}]({transcript})")
        if trace := report.linked_trace_path(run):
            lines.append(f"  - trace: [{trace}]({trace}) ({len(run.trace.tool_calls)} tool calls)")
        return "\n".join(lines)

    @staticmethod
    def _missed_lines(run: RunResult, name: str, report: SuiteReport) -> list[str]:
        """'❌ **name** value (needs …)', then the metric's details one level down."""
        result = run.metrics.get(name)
        if result is None:
            return [f"  - ❌ **{name}**"]
        threshold = report.threshold_for(run.case_id, name)
        needs = f" (needs {threshold_words(threshold)})" if threshold else ""
        return [f"  - ❌ **{name}** {MarkdownText.cell(result.value)}{needs}"] + [
            f"    - {key}: {MarkdownText.one_line(value)}"
            for key, value in result.details.items()
            if value not in EMPTY and key != REASONING
        ]

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
        result, suite = report.result, report.loaded.suite
        ran_models = {c.model for c in report.candidates}
        models = (
            ", ".join(
                f"{m.display_label} ({m.provider} {m.model})" for m in suite.models if m.display_label in ran_models
            )
            or "the DataSet's configured model"
        )
        variants = ", ".join(dict.fromkeys(c.variant for c in report.candidates))
        lines = [
            "## Run details",
            f"- started {MarkdownText.cell(result.started_at)}, finished {MarkdownText.cell(result.finished_at)}",
            f"- models: {models}; variants: {variants}; repeats: {suite.repeats}",
            f"- prices as of {result.pricing_as_of or '–'}",
        ]
        if report.args:
            lines.append(f"- command: `{' '.join(report.args)}`")
        return "\n".join(lines)
