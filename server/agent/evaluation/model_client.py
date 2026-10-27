from threading import Lock

from enthusiast_common.evaluation.base_model_client import BaseModelClient
from enthusiast_common.evaluation.suite import ModelTarget
from enthusiast_common.evaluation.trace import TraceRecorder
from langchain_core.language_models import BaseChatModel

from agent.core.registries.language_models import LanguageModelRegistry
from agent.evaluation.pricing_table import PricingTable, TraceCost
from agent.evaluation.trace_callback_handler import TraceCallbackHandler


class EvalModelClient(BaseModelClient):
    """Sends prompts to a model the evaluation asks besides the agent, recording every call in its own trace so its
    cost stays apart from the agent's.

    target is the default model; a call may name another. Each model's LLM is built on first use, and a model's own
    pricing (ModelTarget.pricing) is added to the table then.
    """

    def __init__(self, target: ModelTarget | None, pricing: PricingTable):
        self.target = target
        self._pricing = pricing
        self._recorder = TraceRecorder()
        self._llms: dict[tuple[str, str], BaseChatModel] = {}
        self._lock = Lock()

    def complete(self, prompt: str, model: ModelTarget | None = None) -> str:
        """Ask the given model, or else the default one; raises ValueError when neither is set."""
        target = model or self.target
        if target is None:
            raise ValueError("No model to ask: set it in the suite.")
        return self._llm_for(target).invoke(prompt).text

    def cost(self) -> TraceCost:
        """What every model this client asked has cost so far."""
        return self._pricing.trace_cost(self._recorder.trace)

    def _llm_for(self, target: ModelTarget) -> BaseChatModel:
        """The LLM for a model, built once and shared by every caller naming it."""
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
