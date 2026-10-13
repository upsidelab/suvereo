import string
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, ValidationInfo, model_validator

from ...suite import ModelTarget
from ..base_metric import BASE_DIR


class JudgePromptParams(BaseModel):
    """Params every LLM metric shares: the judge model to ask and an optional custom prompt template."""

    model_config = ConfigDict(extra="forbid")

    #: The placeholders a custom prompt may use; subclasses list theirs. {material} is required.
    PLACEHOLDERS: ClassVar[tuple[str, ...]] = ("material",)

    judge: ModelTarget | None = None
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
