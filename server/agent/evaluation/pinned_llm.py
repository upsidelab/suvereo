from typing import Any, ClassVar

from enthusiast_common.llm import BaseLLM
from enthusiast_common.registry.llm import LanguageModelProvider


class PinnedLLM(BaseLLM):
    """A BaseLLM that builds one provider and model whatever the data set is configured with."""

    PROVIDER: ClassVar[str]
    MODEL: ClassVar[str]

    _classes: ClassVar[dict[tuple[str, str], type["PinnedLLM"]]] = {}

    @classmethod
    def for_model(cls, provider: str, model: str) -> type["PinnedLLM"]:
        """The pinned class for a provider NAME and model, one cached class per pair."""
        key = (provider, model)
        if key not in PinnedLLM._classes:
            PinnedLLM._classes[key] = type(
                f"Pinned{provider}LLM[{model}]", (PinnedLLM,), {"PROVIDER": provider, "MODEL": model}
            )
        return PinnedLLM._classes[key]

    def _resolve_target(self, data_set_id: Any) -> tuple[type[LanguageModelProvider], str]:
        return self._llm_registry.provider_class_by_name(self.PROVIDER), self.MODEL
