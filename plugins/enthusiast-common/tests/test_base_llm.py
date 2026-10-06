from unittest.mock import MagicMock

from enthusiast_common.llm import BaseLLM
from enthusiast_common.registry.llm import LanguageModelProvider


class RecordingProvider(LanguageModelProvider):
    STREAMING_AVAILABLE = True

    def provide_language_model(self, callbacks=None):
        return ("plain", self._model, callbacks)

    def provide_streaming_language_model(self, callbacks=None):
        return ("streaming", self._model, callbacks)

    def model_name(self):
        return self._model

    @staticmethod
    def available_models():
        return []

    @staticmethod
    def prepare_image_object(file_object):
        return None

    @staticmethod
    def prepare_file_object(file_object):
        return None


class OtherProvider(RecordingProvider):
    pass


def _llm(streaming=False, callbacks=None):
    registry = MagicMock()
    registry.provider_for_dataset.return_value = RecordingProvider
    data_set_repo = MagicMock()
    data_set_repo.get_by_id.return_value.language_model = "model-from-data-set"
    return BaseLLM(llm_registry=registry, data_set_repo=data_set_repo, callbacks=callbacks, streaming=streaming)


class TestBaseLLM:
    def test_create_builds_the_data_set_model(self):
        assert _llm().create(1) == ("plain", "model-from-data-set", None)

    def test_create_passes_the_callbacks_to_the_provider(self):
        handler = object()

        assert _llm(callbacks=[handler]).create(1)[2] == [handler]

    def test_create_uses_the_streaming_model_when_asked_and_available(self):
        assert _llm(streaming=True).create(1)[0] == "streaming"

    def test_overriding_resolve_target_changes_what_is_built(self):
        class PinnedLLM(BaseLLM):
            def _resolve_target(self, data_set_id):
                return OtherProvider, "pinned-model"

        llm = _llm()
        pinned = PinnedLLM(llm_registry=llm._llm_registry, data_set_repo=llm._data_set_repo)

        assert pinned.create(1) == ("plain", "pinned-model", None)
