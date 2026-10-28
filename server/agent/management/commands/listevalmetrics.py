from django.core.management.base import BaseCommand
from suvereo_common.evaluation.metrics import BaseMetric
from suvereo_common.evaluation.metrics.auto import AUTO_METRICS
from suvereo_common.evaluation.metrics.builtins import BUILTIN_METRICS
from pydantic import BaseModel


class Command(BaseCommand):
    help = "Lists the built-in evaluation metrics with their value type, params and description."

    def handle(self, *args, **options):
        for metric in BUILTIN_METRICS:
            heading = f"{metric.NAME}: {metric.VALUE_TYPE}{self._measured_on(metric)}"
            self.stdout.write(self.style.MIGRATE_HEADING(heading))
            description = (metric.__doc__ or "").strip().splitlines()
            self.stdout.write(f"  {description[0] if description else ''}")
            for line in self._params_lines(metric.PARAMS):
                self.stdout.write(f"    {line}")

    @staticmethod
    def _measured_on(metric: type[BaseMetric]) -> str:
        """Which runs an auto metric is measured on with no configuration; empty for configured metrics."""
        if metric not in AUTO_METRICS:
            return ""
        if len(metric.KINDS) > 1:
            return " (measured on every run)"
        return f" (measured on every {metric.KINDS[0]} run)"

    @staticmethod
    def _params_lines(params: type[BaseModel]) -> list[str]:
        """One line per param: its name, whether it is required, and its description."""
        lines = []
        for name, field in params.model_fields.items():
            required = "required" if field.is_required() else "optional"
            description = f": {field.description}" if field.description else ""
            lines.append(f"{field.alias or name} ({required}){description}")
        return lines
