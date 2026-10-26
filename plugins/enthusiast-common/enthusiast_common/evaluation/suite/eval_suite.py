from typing import Any

from pydantic import Field, model_validator

from ...utils import deep_merge
from .agent_ref import AgentRef
from .any_eval_case import AnyEvalCase
from .base import EvalModel
from .eval_case import EvalCase
from .integration_config import IntegrationConfig
from .metric_config import MetricConfig
from .model_target import ModelTarget
from .prompt_variant import PromptVariant
from .report_name import DEFAULT_REPORTS, ReportName
from .suite_kind import SuiteKind

CasesSpec = str | list[str | AnyEvalCase]


class EvalSuite(EvalModel):
    """An evaluation suite as written in suite.yaml; only agent, metrics and cases are required."""

    name: str = Field(default="", description="Defaults to the suite's directory name.")
    description: str = ""
    agent: AgentRef
    kind: SuiteKind | None = Field(
        default=None,
        description="Defaults to execution when the agent type has an execution definition, otherwise conversation.",
    )
    execution_key: str | None = Field(default=None, description="Optional when the agent type has one definition.")
    integrations: list[IntegrationConfig] = []
    models: list[ModelTarget] = Field(default=[], description="Empty runs the DataSet's configured model.")
    variants: list[PromptVariant] = []
    judge: ModelTarget | None = None
    repeats: int = Field(default=1, ge=1)
    budget_usd: float | None = Field(default=None, gt=0)
    min_pass_rate: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Minimum pass rate per candidate for the run to succeed; without it the run has no verdict.",
    )
    metrics: list[MetricConfig] = Field(min_length=1)
    reports: list[ReportName] = Field(default=DEFAULT_REPORTS, description="Outputs to write besides summary.json.")
    cases: CasesSpec = Field(description="Case files or directories (suite-relative), inline cases, or a list of both.")

    @model_validator(mode="after")
    def _names_are_unique(self) -> "EvalSuite":
        for kind, names in (
            ("metric", [m.name for m in self.metrics]),
            ("variant", [v.name for v in self.variants]),
            ("model label", [m.display_label for m in self.models]),
            ("integration", [i.key for i in self.integrations]),
        ):
            duplicates = sorted({n for n in names if names.count(n) > 1})
            if duplicates:
                raise ValueError(f"Duplicate {kind} name(s): {', '.join(duplicates)}. Give each a distinct name.")
        return self

    @classmethod
    def json_schema(cls) -> dict[str, Any]:
        """The JSON Schema of suite.yaml, with keys spelled as in YAML (e.g. ``class``, ``in``)."""
        return cls.model_json_schema(by_alias=True)

    def integrations_for(self, case: EvalCase) -> list[IntegrationConfig]:
        """The suite's integrations with the case's overrides deep-merged in; a case's behaviour for a method replaces the suite's."""
        overrides = {i.key: i for i in case.integrations}
        merged = [self._override(i, overrides.pop(i.key)) if i.key in overrides else i for i in self.integrations]
        return merged + list(overrides.values())

    def metrics_for(self, case: EvalCase) -> list[MetricConfig]:
        """The suite's metrics, the case's replacing those of the same name, plus any the case adds."""
        overrides = {m.name: m for m in case.metrics}
        merged = [overrides.pop(m.name, m) for m in self.metrics]
        return merged + list(overrides.values())

    @staticmethod
    def _override(base: IntegrationConfig, override: IntegrationConfig) -> IntegrationConfig:
        config = deep_merge({k: v for k, v in base.config.items() if k != "behaviour"}, override.config)
        if "behaviour" in base.config or "behaviour" in override.config:
            config["behaviour"] = {**base.config.get("behaviour", {}), **override.config.get("behaviour", {})}
        return base.model_copy(update={"config": config})
