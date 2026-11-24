import json
from typing import Any

from django.core.management.base import BaseCommand
from suvereo_common.evaluation.suite import EvalSuite


class Command(BaseCommand):
    help = "Prints the JSON Schema of suite.yaml, e.g. for editor completion and validation."

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(json.dumps(EvalSuite.json_schema(), indent=2))
