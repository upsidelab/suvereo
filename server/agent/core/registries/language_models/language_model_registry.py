from importlib import import_module

from suvereo_common.registry import BaseLanguageModelRegistry
from suvereo_common.registry.llm import LanguageModelProvider
from suvereo_common.repositories import BaseDataSetRepository
from utils.base_registry import BaseRegistry

from agent.core.repositories import DjangoDataSetRepository
from pecl import settings


class LanguageModelRegistry(BaseRegistry[LanguageModelProvider], BaseLanguageModelRegistry):
    plugin_base = LanguageModelProvider

    def __init__(self, data_set_repo: BaseDataSetRepository | None = None):
        if data_set_repo is None:
            module_path, class_name = settings.CATALOG_MODELS["data_set"].rsplit(".", 1)
            data_set_model = getattr(import_module(module_path), class_name)
            self._data_set_repo = DjangoDataSetRepository(data_set_model)
        else:
            self._data_set_repo = data_set_repo

    def get_provider_classes(self) -> list[type[LanguageModelProvider]]:
        return [self._get_plugin_class_by_path(path) for path in self._get_plugin_paths()]

    def _get_provider_classes_by_name(self) -> dict[str, type[LanguageModelProvider]]:
        return {cls.NAME: cls for cls in self.get_provider_classes()}

    def provider_class_by_name(self, name: str) -> type[LanguageModelProvider]:
        return self._get_provider_classes_by_name()[name]

    def provider_for_dataset(self, data_set_id: int) -> type[LanguageModelProvider]:
        data_set = self._data_set_repo.get_by_id(data_set_id)
        return self.provider_class_by_name(data_set.language_model_provider)

    @staticmethod
    def _get_plugin_paths() -> list[str]:
        return settings.CATALOG_LANGUAGE_MODEL_PROVIDERS
