from typing import Any, Type

from enthusiast_common.registry.llm import LanguageModelProvider
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseLanguageModel

from ..registry import BaseLanguageModelRegistry
from ..repositories import BaseDataSetRepository


class BaseLLM:
    def __init__(
        self,
        llm_registry: BaseLanguageModelRegistry,
        data_set_repo: BaseDataSetRepository,
        callbacks: list[BaseCallbackHandler] = None,
        streaming: bool = False,
    ):
        self._llm_registry = llm_registry
        self._streaming = streaming
        self._callbacks = callbacks
        self._data_set_repo = data_set_repo

    def create(self, data_set_id: Any) -> BaseLanguageModel:
        """Build the language model the data set is configured to use."""
        provider_class, model = self._resolve_target(data_set_id)
        return self._build(provider_class, model)

    def _resolve_target(self, data_set_id: Any) -> tuple[Type[LanguageModelProvider], str]:
        """The provider class and model name to build; override to choose them some other way."""
        data_set = self._data_set_repo.get_by_id(data_set_id)
        return self._llm_registry.provider_for_dataset(data_set_id), data_set.language_model

    def _build(self, provider_class: Type[LanguageModelProvider], model: str) -> BaseLanguageModel:
        provider = provider_class(model)
        if self._streaming and provider.STREAMING_AVAILABLE:
            return provider.provide_streaming_language_model(callbacks=self._callbacks)
        return provider.provide_language_model(callbacks=self._callbacks)
