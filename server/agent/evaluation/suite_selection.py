from pathlib import Path

from pydantic import BaseModel, Field
from suvereo_common.evaluation.errors import EvalSuiteError
from suvereo_common.evaluation.loaded_suite import LoadedSuite
from suvereo_common.evaluation.suite import DEFAULT_VARIANT, ModelTarget, PromptVariant


class SuiteSelection(BaseModel):
    """Narrows a suite to part of it for one run (the runeval options), without editing suite.yaml; empty fields keep
    what the suite has."""

    models: list[str] = Field(default=[], description="Suite model labels, or Provider:model for a model it lacks.")
    variants: list[str] = Field(default=[], description="Variant names; the default variant always runs.")
    prompt_file: Path | None = Field(default=None, description="An ad-hoc variant named after the file.")
    case_ids: list[str] = []
    tags: list[str] = Field(default=[], description="Keeps cases with any of these tags.")
    repeats: int | None = Field(default=None, ge=1)

    def apply(self, loaded: LoadedSuite) -> LoadedSuite:
        """The suite narrowed to the selection; raises EvalSuiteError for a name the suite doesn't have."""
        suite = loaded.suite
        changes = {
            "models": [self._model_target(spec, suite.models) for spec in dict.fromkeys(self.models)] or suite.models,
            "variants": self._variants(suite.variants),
            "repeats": self.repeats or suite.repeats,
        }
        cases = loaded.cases
        if unknown := sorted(set(self.case_ids) - {case.id for case in cases}):
            raise EvalSuiteError(f"No case(s) with id {', '.join(unknown)}.")
        if self.case_ids:
            cases = [case for case in cases if case.id in self.case_ids]
        if self.tags:
            cases = [case for case in cases if set(case.tags) & set(self.tags)]
        if not cases:
            raise EvalSuiteError("No case matches the selection.")
        return loaded.model_copy(update={"suite": suite.model_copy(update=changes), "cases": cases})

    @staticmethod
    def _model_target(spec: str, models: list[ModelTarget]) -> ModelTarget:
        """A suite model by label, else Provider:model."""
        if model := next((m for m in models if m.display_label == spec), None):
            return model
        provider, separator, name = spec.partition(":")
        if not (separator and provider and name):
            labels = ", ".join(m.display_label for m in models) or "none"
            raise EvalSuiteError(f"Model '{spec}' is neither a suite model ({labels}) nor Provider:model.")
        return ModelTarget(provider=provider, model=name)

    def _variants(self, variants: list[PromptVariant]) -> list[PromptVariant]:
        selected = variants
        if self.variants:
            if unknown := sorted(set(self.variants) - {v.name for v in variants}):
                raise EvalSuiteError(f"No variant(s) named {', '.join(unknown)}.")
            selected = [v for v in variants if v.name in self.variants]
        if self.prompt_file is None:
            return selected
        name = self.prompt_file.stem
        if name in {DEFAULT_VARIANT, *(v.name for v in variants)}:
            raise EvalSuiteError(f"Prompt file {self.prompt_file.name} is named like an existing variant; rename it.")
        ad_hoc = PromptVariant(name=name, system_prompt_file=str(self.prompt_file.resolve()))
        return [*selected, ad_hoc]
