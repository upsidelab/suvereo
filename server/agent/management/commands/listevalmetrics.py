from django.core.management.base import BaseCommand
from enthusiast_common.evaluation.metrics.auto import AUTO_METRICS
from enthusiast_common.evaluation.metrics.builtins import BUILTIN_METRICS
from pydantic import BaseModel


class Command(BaseCommand):
    help = "Lists the built-in evaluation metrics with their value type, params and description."

    def handle(self, *args, **options):
        for metric in BUILTIN_METRICS:
            measured_always = " (measured on every run)" if metric in AUTO_METRICS else ""
            self.stdout.write(self.style.MIGRATE_HEADING(f"{metric.NAME}: {metric.VALUE_TYPE}{measured_always}"))
            description = (metric.__doc__ or "").strip().splitlines()
            self.stdout.write(f"  {description[0] if description else ''}")
            for line in self._params_lines(metric.PARAMS):
                self.stdout.write(f"    {line}")

    @staticmethod
    def _params_lines(params: type[BaseModel]) -> list[str]:
        """One line per param: its name, whether it is required, and its description."""
        lines = []
        for name, field in params.model_fields.items():
            required = "required" if field.is_required() else "optional"
            description = f": {field.description}" if field.description else ""
            lines.append(f"{field.alias or name} ({required}){description}")
        return lines
