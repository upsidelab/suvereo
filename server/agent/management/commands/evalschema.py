import json

from django.core.management.base import BaseCommand
from enthusiast_common.evaluation.suite import EvalSuite


class Command(BaseCommand):
    help = "Prints the JSON Schema of suite.yaml, e.g. for editor completion and validation."

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(EvalSuite.json_schema(), indent=2))
