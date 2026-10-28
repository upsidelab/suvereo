import json
import logging
import sys
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Iterator

from django.core.management.base import BaseCommand
from suvereo_common.evaluation.errors import EvalSuiteError
from suvereo_common.evaluation.suite import ReportName
from pydantic import TypeAdapter, ValidationError

from agent.evaluation.aggregation import PASS_RATE
from agent.evaluation.reports import ExitCode, MarkdownText, RunHistory, SummaryFile, SummaryJsonWriter
from agent.evaluation.runner import SuiteRunOptions
from agent.evaluation.suite_evaluation import SuiteEvaluation, SuiteEvaluationOutcome
from agent.evaluation.suite_loader import SuiteLoader
from agent.evaluation.suite_selection import SuiteSelection

logger = logging.getLogger(__name__)

RECORDED_OPTIONS = [
    "model",
    "variant",
    "prompt_file",
    "case",
    "tag",
    "rerun_failed",
    "repeats",
    "baseline",
    "budget",
    "parallel",
    "reports",
    "note",
    "allow_real_integrations",
    "keep_run_data",
]
HISTORY_COLUMNS = ["run", "candidate", "pass_rate", "flaky_rate", "cost_mean_usd", "git_sha", "note"]


class Command(BaseCommand):
    help = (
        "Runs an agent evaluation suite and writes summary.json and the selected reports to "
        "<suite_dir>/results/<run>/. Exits 0 when every candidate reaches the pass threshold, 1 when one doesn't, "
        "2 for an invalid suite, 3 when the budget stopped the run and 4 for any other error."
    )

    def add_arguments(self, parser):
        parser.add_argument("suite", type=Path, help="path to suite.yaml")
        parser.add_argument("--model", action="append", default=[], help="a suite model label or Provider:model")
        parser.add_argument("--variant", action="append", default=[], help="a variant to run besides the default")
        parser.add_argument("--prompt-file", type=Path, help="a system prompt to try as an extra variant")
        parser.add_argument("--case", action="append", default=[], help="a case id to run")
        parser.add_argument("--tag", action="append", default=[], help="run the cases with this tag")
        parser.add_argument(
            "--rerun-failed", metavar="SUMMARY", help="run the cases a summary.json (or 'latest') failed"
        )
        parser.add_argument("--repeats", type=int, help="runs per case, model and variant")
        parser.add_argument("--baseline", metavar="SUMMARY", help="compare against a summary.json, or 'latest'")
        parser.add_argument("--budget", type=float, help="USD limit, overriding the suite's budget_usd")
        parser.add_argument("--parallel", type=int, help="runs in flight at once (default 1)")
        parser.add_argument("--reports", help="comma-separated reports to write, overriding the suite's reports")
        parser.add_argument("--note", default="", help="recorded in the history with this run, e.g. a hypothesis")
        parser.add_argument("--format", choices=["text", "json"], default="text", help="json prints summary.json")
        parser.add_argument("--history", action="store_true", help="print the suite's run history and exit")
        parser.add_argument("--allow-real-integrations", action="store_true", help="let unmocked integrations run")
        parser.add_argument("--keep-run-data", action="store_true", help="keep conversations and sandboxes")

    def handle(self, *args, **options):
        suite_path: Path = options["suite"]
        if options["history"]:
            self._print_history(RunHistory(suite_path.resolve().parent))
            return
        try:
            evaluation = self._build_evaluation(suite_path, options)
        except EvalSuiteError as e:
            self.stderr.write(str(e))
            sys.exit(ExitCode.INVALID_SUITE)
        try:
            with self._logs_to_stderr() if options["format"] == "json" else nullcontext():
                outcome = evaluation.run()
        except Exception as e:
            logger.exception("The evaluation failed")
            self.stderr.write(f"The evaluation failed: {type(e).__name__}: {e}")
            sys.exit(ExitCode.RUNTIME_ERROR)
        self._print_outcome(outcome, options["format"])
        if outcome.verdict.exit_code != ExitCode.PASSED:
            sys.exit(outcome.verdict.exit_code)

    @staticmethod
    @contextmanager
    def _logs_to_stderr() -> Iterator[None]:
        """Point log handlers that write to stdout at stderr while running, so --format json prints only JSON."""
        loggers = [logging.getLogger(), *(logging.getLogger(name) for name in logging.root.manager.loggerDict)]
        handlers = {h for logger in loggers for h in logger.handlers if getattr(h, "stream", None) is sys.stdout}
        for handler in handlers:
            handler.setStream(sys.stderr)
        try:
            yield
        finally:
            for handler in handlers:
                handler.setStream(sys.stdout)

    @staticmethod
    def _build_evaluation(suite_path: Path, options: dict) -> SuiteEvaluation:
        """The evaluation the options describe; raises EvalSuiteError for an invalid suite or option."""
        suite_dir = suite_path.resolve().parent
        case_ids = options["case"]
        if options["rerun_failed"]:
            case_ids = [*case_ids, *SummaryFile.load(options["rerun_failed"], suite_dir).failing_case_ids()]
            if not case_ids:
                raise EvalSuiteError("The summary has no failed runs to rerun.")
        try:
            selection = SuiteSelection(
                models=options["model"],
                variants=options["variant"],
                prompt_file=options["prompt_file"],
                case_ids=case_ids,
                tags=options["tag"],
                repeats=options["repeats"],
            )
            run_options = SuiteRunOptions(
                parallel=1 if options["parallel"] is None else options["parallel"],
                budget_usd=options["budget"],
                allow_real_integrations=options["allow_real_integrations"],
                keep_run_data=options["keep_run_data"],
            )
            reports = None
            if options["reports"] is not None:
                names = [name.strip() for name in options["reports"].split(",") if name.strip()]
                reports = TypeAdapter(list[ReportName]).validate_python(names)
        except ValidationError as e:
            raise EvalSuiteError(f"Invalid option: {e}") from e
        baseline = SummaryFile.load(options["baseline"], suite_dir) if options["baseline"] else None
        return SuiteEvaluation(
            SuiteLoader().load(suite_path, selection),
            run_options,
            reports,
            baseline,
            options["note"],
            Command._command_line(suite_path, options),
        )

    @staticmethod
    def _command_line(suite_path: Path, options: dict) -> list[str]:
        """The run's command as given, rebuilt from its options, for the reports and the history."""
        parts = ["runeval", str(suite_path)]
        for name in RECORDED_OPTIONS:
            flag = f"--{name.replace('_', '-')}"
            values = options[name] if isinstance(options[name], list) else [options[name]]
            for value in values:
                if value is True:
                    parts.append(flag)
                elif value not in (None, False, ""):
                    parts += [flag, str(value)]
        return parts

    def _print_outcome(self, outcome: SuiteEvaluationOutcome, output_format: str) -> None:
        if output_format == "json":
            self.stdout.write(json.dumps(SummaryJsonWriter().summary(outcome.report), indent=2, default=str))
            return
        report, verdict = outcome.report, outcome.verdict
        rows = [
            [c.candidate, len(c.runs), MarkdownText.cell(c.metrics[PASS_RATE].value), MarkdownText.usd(c.cost_mean_usd)]
            for c in report.candidates
        ]
        self.stdout.write(MarkdownText.table(["Candidate", "Runs", "Pass rate", "Cost / run"], rows))
        self.stdout.write(
            f"\nRun {verdict.status}, exit code {int(verdict.exit_code)}; spent "
            f"{MarkdownText.usd(report.result.spent_usd)}. Reports in {outcome.run_dir}"
        )

    def _print_history(self, history: RunHistory) -> None:
        entries = history.entries()
        if not entries:
            self.stdout.write(f"No runs recorded in {history.path} yet.")
            return
        rows = [[MarkdownText.cell(entry.get(column)) for column in HISTORY_COLUMNS] for entry in entries]
        self.stdout.write(MarkdownText.table(HISTORY_COLUMNS, rows))
