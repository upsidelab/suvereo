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
        """Build the language model to use for a data set.

        Args:
            data_set_id: The data set whose model is built, unless ``_resolve_target`` chooses otherwise.

        Returns:
            The provider's language model, streaming when requested and available.
        """
        provider_class, model = self._resolve_target(data_set_id)
        return self._build(provider_class, model)

    def _resolve_target(self, data_set_id: Any) -> tuple[Type[LanguageModelProvider], str]:
        """Choose the provider and model to build; override to pin them.

        Args:
            data_set_id: The data set being built for.

        Returns:
            The provider class and the model name, by default those configured on the data set.
        """
        data_set = self._data_set_repo.get_by_id(data_set_id)
        return self._llm_registry.provider_for_dataset(data_set_id), data_set.language_model

    def _build(self, provider_class: Type[LanguageModelProvider], model: str) -> BaseLanguageModel:
        provider = provider_class(model)
        if self._streaming and provider.STREAMING_AVAILABLE:
            return provider.provide_streaming_language_model(callbacks=self._callbacks)
        return provider.provide_language_model(callbacks=self._callbacks)
