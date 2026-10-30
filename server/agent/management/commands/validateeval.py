import sys
from pathlib import Path

from django.core.management.base import BaseCommand
from suvereo_common.evaluation.errors import EvalSuiteError

from agent.evaluation.reports import ExitCode
from agent.evaluation.runner import SuiteRunner
from agent.evaluation.suite_loader import SuiteLoader


class Command(BaseCommand):
    help = "Checks an agent evaluation suite without running it or spending tokens; exits 2 when it is invalid."

    def add_arguments(self, parser):
        parser.add_argument("suite", type=Path, help="path to suite.yaml")

    def handle(self, *args, **options):
        try:
            loaded = SuiteLoader().load(options["suite"])
        except EvalSuiteError as e:
            self.stderr.write(str(e))
            sys.exit(ExitCode.INVALID_SUITE)
        runs = SuiteRunner(loaded).planned_run_count
        self.stdout.write(
            self.style.SUCCESS(f"Suite '{loaded.suite.name}' is valid: ")
            + f"{len(loaded.cases)} case(s), {runs} planned run(s)."
        )
