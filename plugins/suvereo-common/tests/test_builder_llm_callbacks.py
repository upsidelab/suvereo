from unittest.mock import MagicMock

from langchain_core.callbacks import BaseCallbackHandler
from suvereo_common.builder import AgentBuilder
from suvereo_common.config.base import CallbackHandlerConfig


class RecordingHandler(BaseCallbackHandler):
    pass


class RecordingLLM:
    """Stands in for ``BaseLLM``, keeping what the builder passed it."""

    def __init__(self, llm_registry, data_set_repo, callbacks=None, streaming=False):
        self.callbacks = callbacks
        self.streaming = streaming

    def create(self, data_set_id):
        return self


def _builder(callbacks=None) -> AgentBuilder:
    config = MagicMock()
    config.llm.llm_class = RecordingLLM
    config.llm.callbacks = callbacks
    config.registry.llm.providers = None
    builder = AgentBuilder(agent_class=MagicMock(), config=config, conversation_id=1, streaming=True)
    builder._repositories = MagicMock()
    builder._data_set_id = 1
    return builder


class TestDefaultLLMCallbacks:
    """Tools, retrievers and the memory compactor use the default LLM, so its calls must be observable too."""

    def test_default_llm_gets_the_configured_callbacks(self):
        llm = _builder([CallbackHandlerConfig(handler_class=RecordingHandler)])._build_default_llm()

        assert [type(handler) for handler in llm.callbacks] == [RecordingHandler]

    def test_default_llm_has_no_callbacks_when_none_are_configured(self):
        assert _builder()._build_default_llm().callbacks is None

    def test_default_llm_does_not_stream_even_when_the_agent_does(self):
        assert _builder()._build_default_llm().streaming is False
