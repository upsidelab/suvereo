import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, SchemaError
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator

from ..base_metric import BASE_DIR, BaseMetric
from ..metric_context import MetricContext
from ..metric_result import MetricResult

MAX_REPORTED_ERRORS = 5


class JsonSchemaParams(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    json_schema: dict[str, Any] | None = Field(default=None, alias="schema")
    schema_file: Path | None = None

    @model_validator(mode="after")
    def _load_schema(self, info: ValidationInfo) -> "JsonSchemaParams":
        if (self.json_schema is None) == (self.schema_file is None):
            raise ValueError("Set exactly one of 'schema' or 'schema_file'.")
        try:
            if self.schema_file is not None:
                if not self.schema_file.is_absolute() and info.context and info.context.get(BASE_DIR):
                    self.schema_file = info.context[BASE_DIR] / self.schema_file
                self.json_schema = json.loads(self.schema_file.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(self.json_schema)
        except (OSError, json.JSONDecodeError, SchemaError) as e:
            raise ValueError(f"Unusable JSON Schema: {e}") from e
        return self


class JsonSchema(BaseMetric):
    """Whether the output conforms to a JSON Schema, given inline as 'schema' or as a 'schema_file'."""

    NAME = "json_schema"
    VALUE_TYPE = "bool"
    PARAMS = JsonSchemaParams

    def measure(self, context: MetricContext) -> MetricResult:
        if context.trace.output is None:
            return MetricResult(value=False, details={"reason": "the run produced no output"})
        errors = sorted(Draft202012Validator(self.params.json_schema).iter_errors(context.trace.output), key=str)
        messages = [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors]
        return MetricResult(value=not errors, details={"errors": messages[:MAX_REPORTED_ERRORS]} if errors else {})
