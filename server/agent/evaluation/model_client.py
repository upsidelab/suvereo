from threading import Lock

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from suvereo_common.evaluation.base_model_client import BaseModelClient
from suvereo_common.evaluation.chat_message import ChatMessage
from suvereo_common.evaluation.suite import ModelTarget
from suvereo_common.evaluation.trace import TraceRecorder

from agent.core.registries.language_models import LanguageModelRegistry
from agent.evaluation.pricing_table import PricingTable, TraceCost
from agent.evaluation.trace_callback_handler import TraceCallbackHandler


class EvalModelClient(BaseModelClient):
    def __init__(self, target: ModelTarget | None, pricing: PricingTable):
        self.target = target
        self._pricing = pricing
        self._recorder = TraceRecorder()
        self._llms: dict[tuple[str, str], BaseChatModel] = {}
        self._lock = Lock()

    def chat(self, messages: list[ChatMessage], system: str | None = None, model: ModelTarget | None = None) -> str:
        target = model or self.target
        if target is None:
            raise ValueError("No model to ask: set 'judge' in the suite or in the metric's params.")
        sent = [SystemMessage(system)] if system else []
        sent += [HumanMessage(m.text) if m.role == "user" else AIMessage(m.text) for m in messages]
        return self._llm_for(target).invoke(sent).text

    def cost(self) -> TraceCost:
        return self._pricing.trace_cost(self._recorder.trace)

    def _llm_for(self, target: ModelTarget) -> BaseChatModel:
        key = (target.provider, target.model)
        with self._lock:
            if key not in self._llms:
                if target.pricing is not None:
                    self._pricing = self._pricing.with_overrides({target.model: target.pricing})
                provider_class = LanguageModelRegistry().provider_class_by_name(target.provider)
                self._llms[key] = provider_class(target.model).provide_language_model(
                    callbacks=[TraceCallbackHandler(self._recorder)]
                )
            return self._llms[key]
