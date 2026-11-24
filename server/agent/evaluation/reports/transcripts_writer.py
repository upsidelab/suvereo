from pathlib import Path

from suvereo_common.evaluation.suite import ConversationEvalCase, SuiteKind

from agent.evaluation.reports.base_report_writer import BaseReportWriter
from agent.evaluation.reports.markdown_text import MarkdownText
from agent.evaluation.reports.suite_report import SuiteReport
from agent.evaluation.reports.transcript_markdown import TranscriptMarkdown
from agent.evaluation.runner import RunResult


class TranscriptsWriter(BaseReportWriter):
    NAME = "transcripts"

    def write(self, report: SuiteReport, run_dir: Path) -> list[Path]:
        if report.kind != SuiteKind.CONVERSATION:
            return []
        written = []
        for run in report.runs:
            path = run_dir / report.transcript_path(run)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self._transcript(run, report), encoding="utf-8")
            written.append(path)
        return written

    @staticmethod
    def _transcript(run: RunResult, report: SuiteReport) -> str:
        case = next((c for c in report.cases if c.id == run.case_id), None)
        lines = [
            f"# {run.case_id} · {run.candidate} · repeat {run.repeat}",
            f"- passed: {MarkdownText.cell(run.passed)}",
            f"- ended: {TranscriptMarkdown.ending(run.trace)}",
        ]
        user = case.simulated_user if isinstance(case, ConversationEvalCase) else None
        if user is not None:
            about = {"goal": user.goal, "persona": user.persona, "facts": user.facts}
            lines += [f"- {name}: {MarkdownText.one_line(value)}" for name, value in about.items() if value]
        if run.trace.error:
            lines.append(f"- error: {MarkdownText.one_line(run.trace.error)}")
        if trace := report.linked_trace_path(run):
            lines.append(f"- trace: [{trace}](../{trace})")
        sections = ["\n".join(lines), TranscriptMarkdown.turns(run.trace) or "No turns were taken."]
        return "\n\n".join(sections) + "\n"
