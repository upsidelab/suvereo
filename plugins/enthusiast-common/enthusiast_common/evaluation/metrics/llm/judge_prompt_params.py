import string
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, ValidationInfo, model_validator

from ...suite import ModelTarget, SuiteKind
from ..base_metric import BASE_DIR
from ..metric_context import MetricContext
from .judge_material import JudgeMaterial, Section


class JudgePromptParams(BaseModel):
    """Params every LLM metric shares: the judge model to ask, what it sees of the run (by default, DEFAULT_INCLUDE
    for the run's kind) and an optional custom prompt template."""

    model_config = ConfigDict(extra="forbid")

    #: The placeholders a custom prompt may use; subclasses list theirs. {material} is required.
    PLACEHOLDERS: ClassVar[tuple[str, ...]] = ("material",)
    #: The sections the judge sees when the suite sets no 'include', per suite kind; subclasses set theirs.
    DEFAULT_INCLUDE: ClassVar[dict[SuiteKind, list[Section]]] = {
        SuiteKind.EXECUTION: ["outcome", "output"],
        SuiteKind.CONVERSATION: ["outcome", "transcript"],
    }

    judge: ModelTarget | None = None
    include: list[Section] | None = None
    prompt: str | None = None
    prompt_file: Path | None = None

    @model_validator(mode="after")
    def _load_and_check_prompt(self, info: ValidationInfo) -> "JudgePromptParams":
        if self.prompt is not None and self.prompt_file is not None:
            raise ValueError("Set at most one of 'prompt' or 'prompt_file'.")
        if self.prompt_file is not None:
            if not self.prompt_file.is_absolute() and info.context and info.context.get(BASE_DIR):
                self.prompt_file = info.context[BASE_DIR] / self.prompt_file
            try:
                self.prompt = self.prompt_file.read_text(encoding="utf-8")
            except OSError as e:
                raise ValueError(f"Cannot read prompt file: {e}") from e
        if self.prompt is not None:
            self._check_placeholders(self.prompt)
        return self

    def include_for(self, context: MetricContext) -> list[Section]:
        """The sections the judge sees of this run: the suite's 'include', or the default for the run's kind."""
        return self.include if self.include is not None else self.DEFAULT_INCLUDE[context.kind]

    def fits(self, kind: SuiteKind) -> bool:
        """Whether runs of this kind have every section the judge is shown."""
        return JudgeMaterial.fits(self.include or [], kind)

    def _check_placeholders(self, template: str) -> None:
        try:
            used = {field for _, field, _, _ in string.Formatter().parse(template) if field is not None}
        except ValueError as e:
            raise ValueError(f"Invalid prompt template ({e}); write literal braces as {{{{ and }}}}.") from e
        unknown = sorted(used - set(self.PLACEHOLDERS))
        if unknown:
            raise ValueError(f"Unknown prompt placeholder(s) {unknown}; use {list(self.PLACEHOLDERS)}.")
        if "material" not in used:
            raise ValueError("The prompt must include {material}, where the run details go.")
